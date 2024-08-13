version development

workflow convert_allencell {
    input {
        Directory raw_images
        String docker
    }

    call convert_allencell_task {
        input:
        raw_images, docker
    }

    output {
        Directory images = convert_allencell_task.images_out
        File metadata_csv = convert_allencell_task.metadata_csv
    }
}

task convert_allencell_task {
    input {
        Directory raw_images
        Int cpu = 8 # 64
        Int shards = cpu*4
        String docker
    }

    command <<<
        set -euo pipefail

        n_images=$(ls -1 ~{raw_images} | wc -l)
        >&2 echo "Images in: $n_images"

        # prepare shard subdirectories with symlinks to each file under raw_images
        shard=1
        for fn in $(ls -1 '~{raw_images}'); do
            mkdir -p shards/$shard/allencell
            ln -s $(realpath "~{raw_images}/${fn}") "shards/${shard}/allencell/${fn}"
            shard=$((shard+1))
            if [ $shard -gt ~{shards} ]; then
                shard=1
            fi
        done

        # in parallel: cd into each shard subdirectory and run convert_allencell.py
        >&2 parallel --verbose --tag 'echo "shard {} start" && cd shards/{} && python3 /SubCell/convert_allencell.py && echo "shard {} done"' ::: $(seq 1 ~{shards})

        # collect all output files into a single directory
        mkdir -p allencell
        find shards -name '*.png' -exec mv {} allencell/ \;
        n_images_out=$(ls -1 allencell | wc -l)
        >&2 echo "Images out: $n_images_out"

        # concatenate all the shards' metadata.csv (avoiding duplicating the header line)
        head -n 1 shards/1/result/allencell/metadata.csv > metadata.csv
        find shards -name metadata.csv -exec tail -n +2 {} \; >> metadata.csv
    >>>

    runtime {
        docker: docker
        cpu: cpu
        memory: "${cpu*4}G"
    }

    output {
        Directory images_out = "allencell"
        File metadata_csv = "metadata.csv"
    }
}
