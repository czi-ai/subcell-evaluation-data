version development

workflow convert_allencell {
    input {
        Array[Directory] shards
        String docker
    }

    call convert_allencell_task {
        input:
        shards, docker
    }

    call format_allencell_metadata {
        input:
        metadata_csv = convert_allencell_task.metadata_csv,
        docker
    }

    output {
        Directory images = convert_allencell_task.images_out
        File metadata_csv = convert_allencell_task.metadata_csv
        File metadata_formatted_csv = format_allencell_metadata.metadata_formatted_csv
    }
}

task convert_allencell_task {
    input {
        Array[Directory] shards
        Int cpu = 96
        String docker
    }

    File shards_manifest = write_lines(shards)

    command <<<
        set -euo pipefail

        n_images=0
        # prepare shard subdirectories
        while read -r dn; do
            mkdir -p shards/$n_images
            ln -s "$(realpath "$dn")" "shards/${n_images}/allencell"
            n_images=$((n_images + $(ls -1 "$dn" | wc -l)))
        done < '~{shards_manifest}'
        >&2 echo "Images in: $n_images"

        # in parallel: cd into each shard subdirectory and run convert_allencell.py
        >&2 parallel --verbose --tag 'echo "shard {} start" && cd shards/{} && python3 /SubCell/convert_allencell.py && echo "shard {} done"' ::: $(ls -1 shards)

        # collect all output files into one directory tree
        find shards -name '*.png' > all_png.txt
        mkdir -p allencell/intermediate allencell/resized
        fgrep _resized.png all_png.txt | xargs -P 16 -I{} mv {} allencell/resized/
        fgrep -v _resized.png all_png.txt | xargs -P 16 -I{} mv {} allencell/intermediate/
        n_images_out=$(find allencell -name '*.png' | wc -l)
        >&2 echo "Images out: $n_images_out"

        # concatenate all the shards' metadata.csv (avoiding duplicating the header line)
        head -n 1 shards/0/result/allencell/metadata.csv > allencell.metadata.csv
        find shards -name metadata.csv -exec tail -n +2 {} \; >> allencell.metadata.csv
    >>>

    runtime {
        docker: docker
        cpu: cpu
        memory: "${cpu*3}G"
    }

    output {
        Directory images_out = "allencell"
        File metadata_csv = "allencell.metadata.csv"
    }
}

task format_allencell_metadata {
    input {
        File metadata_csv
        String docker
    }

    command <<<
        set -euo pipefail
        cp '~{metadata_csv}' allencell.metadata.csv
        python3 /SubCell/metadata/format_metadata_allencell.py
    >>>

    runtime {
        cpu: 2
        memory: "16G"
        docker: docker
    }

    output {
        File metadata_formatted_csv = "allencell.metadata.formatted.csv"
    }
}
