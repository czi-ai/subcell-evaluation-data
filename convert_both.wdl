version development

import "convert_allencell.wdl" as allencell
import "convert_opencell_stardist.wdl" as opencell

workflow convert_both {
    input {
        Directory allencell_raw_images
        String? opencell_s3bucket
        String? opencell_s3prefix
        String? opencell_pattern
        String docker
    }

    call allencell.convert_allencell {
        input:
        raw_images = allencell_raw_images,
        docker
    }

    call opencell.convert_opencell_stardist {
        input:
        s3bucket = opencell_s3bucket,
        s3prefix = opencell_s3prefix,
        pattern = opencell_pattern,
        docker
    }

    output {
        Directory allencell_images = convert_allencell.images
        File allencell_metadata_csv = convert_allencell.metadata_csv
        Directory opencell_images = convert_opencell_stardist.images
        File opencell_metadata_csv = convert_opencell_stardist.metadata_csv
    }
}
