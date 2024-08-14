version development

workflow convert_opencell_stardist {
    input {
        String? s3bucket
        String? s3prefix
        String? pattern
        String docker
    }

    call localize_images {
        input:
        s3bucket, s3prefix, pattern, docker
    }

    call convert_opencell_stardist_task {
        input:
        images_in = localize_images.images,
        docker
    }

    call format_opencell_metadata {
        input:
        metadata_csv = convert_opencell_stardist_task.metadata_csv,
        docker
    }

    output {
        Directory images = convert_opencell_stardist_task.images_out
        File metadata_csv = convert_opencell_stardist_task.metadata_csv
        File metadata_formatted_csv = format_opencell_metadata.metadata_formatted_csv
    }
}

task localize_images {
    # Localize *_proj.tif images from the czb-opencell public bucket to a scratch Directory.
    # (with all files in one flat directory)
    input {
        String s3bucket = "s3://czb-opencell/"
        String s3prefix = "microscopy/raw/"
        String pattern = "_proj.tif"
        String docker
    }

    command <<<
        set -euxo pipefail
        aws s3 ls --no-sign-request --recursive '~{s3bucket}~{s3prefix}' | grep '~{pattern}' | awk '{print $4}' | shuf > suffixes_pre.txt
        head -n 100 suffixes_pre.txt > suffixes.txt # FIXME

        mkdir opencell
        >&2 parallel --verbose 'aws s3 cp --no-sign-request ~{s3bucket}{} opencell/{/}' :::: suffixes.txt

        # check that all files were downloaded (without filename collisions)
        n_suffixes=$(cat suffixes.txt | wc -l)
        n_files=$(ls -1 opencell | wc -l)
        if [ $n_suffixes -ne $n_files ]; then
            >&2 echo "Error: $n_suffixes suffixes but $n_files files"
            exit 1
        fi
    >>>

    runtime {
        docker: docker
        cpu: 8
        memory: "8G"
    }

    output {
        Directory images = "opencell"
    }
}

task convert_opencell_stardist_task {
    input {
        Directory images_in
        Int cpu = 8 # 64
        Int shards = cpu*4
        String docker
    }

    command <<<
        set -euo pipefail

        n_images=$(ls -1 ~{images_in} | wc -l)
        >&2 echo "Images in: $n_images"

        # prepare shard subdirectories with symlinks to each file under images_in
        shard=1
        for fn in $(ls -1 '~{images_in}'); do
            mkdir -p shards/$shard/opencell
            ln -s $(realpath "~{images_in}/${fn}") "shards/${shard}/opencell/${fn}"
            shard=$((shard+1))
            if [ $shard -gt ~{shards} ]; then
                shard=1
            fi
        done

        # in parallel: cd into each shard subdirectory and run convert_opencell_stardist.py
        # setting HDF5_USE_FILE_LOCKING=FALSE and --retries overcomes some sporadic problems with
        # StarDist reading its TensorFlow model file.
        export HDF5_USE_FILE_LOCKING=FALSE
        >&2 parallel --retries 10 --verbose --tag 'echo "shard {} start" && cd shards/{} && python3 /SubCell/convert_opencell_stardist.py && echo "shard {} done"' ::: $(seq 1 ~{shards})

        # collect all output files into a single directory
        mkdir -p opencell
        find shards -name '*.png' -exec mv {} opencell/ \;
        n_images_out=$(ls -1 opencell | wc -l)
        >&2 echo "Images out: $n_images_out"

        # concatenate all the shards' metadata.csv (avoiding duplicating the header line)
        head -n 1 shards/1/result/opencell/metadata.csv > opencell.metadata.csv
        find shards -name metadata.csv -exec tail -n +2 {} \; >> opencell.metadata.csv
    >>>

    runtime {
        docker: docker
        cpu: cpu
        memory: "${cpu*4}G"
    }

    output {
        Directory images_out = "opencell"
        File metadata_csv = "opencell.metadata.csv"
    }
}

task format_opencell_metadata {
    input {
        File metadata_csv
        String docker
    }

    command <<<
        set -euo pipefail
        cp '~{metadata_csv}' opencell.metadata.csv
        python3 /SubCell/metadata/format_metadata_opencell.py
    >>>

    runtime {
        cpu: 2
        memory: "16G"
        docker: docker
    }

    output {
        File metadata_formatted_csv = "opencell.metadata.formatted.csv"
    }
}
