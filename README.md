# Data Processing for SubCell Evaluation 
This repo contains the code to: 
- Process OpenCell data for evaluating the SubCell models. 
- Put the above processed data into an appropriate S3 bucket.

For license and more information about OpenCell data please see https://opencell.czbiohub.org/download.

## Overview

* `convert_allencell.py` and `convert_opencell_stardist.py` contain the core logic to process OpenCell and AllenCell images. Each runs single-threaded on a local directory of TIFF image files, producing a directory of processed PNG image files and a metadata CSV file.
* `metadata/` has scripts and assets for further post-processing the metadata CSV.
* `Dockerfile` specifies a docker image bundling these scripts with their OS and PyPI dependencies.
* `convert_allencell.wdl` and `convert_opencell_stardist.wdl` are simple WDL workflows for running the dockerized scripts at scale using [AWS HealthOmics](https://aws.amazon.com/healthomics/). So far, a simple scaling approach using GNU parallel on single large worker nodes has sufficed, but the WDL/HealthOmics framework will make it straightforward to scale horizontally, if needed in the future.

## Running on AWS

**Data staging.** Both input datasets reside in public S3 buckets, OpenCell under `s3://czb-opencell/microscopy/raw/` in us-west-2 and AllenCell under `s3://allencell/aics/hipsc_single_cell_image_dataset/` in us-east-1. We assume we want to run in us-west-2, so we can run on OpenCell directly. For AllenCell, we'll copy the dataset to a us-west-2 S3 bucket and in so doing, shard it into 256 subfolders to facilitate parallel processing.

```
# List all the AllenCell raw TIFF images
aws s3 cp s3://allencell/aics/hipsc_single_cell_image_dataset/metadata.csv - | egrep -o 'crop_raw/.*_raw.ome.tif' > allencell_raw_images.txt
# Parallelize S3 inter-region copy into sharded folders
parallel --verbose 'aws s3 cp s3://allencell/aics/hipsc_single_cell_image_dataset/{} "s3://OUR-BUCKET/allencell-sharded/$(( {#} % 256 ))/{/}"' :::: allencell_raw_images.txt
```

**AWS setup and building docker.** We will use the [miniwdl-omics-run](https://github.com/miniwdl-ext/miniwdl-omics-run) local command-line tool to initiate the WDL workflow runs. We assume the tool has been installed (`pip3 install miniwdl-omics-run`) and the one-time AWS account setup steps documented there have been completed.

Building the docker image and pushing it to the `omics` ECR:

```
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_DEFAULT_REGION=$(aws configure get region)
ECR_ENDPT="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com"
aws ecr get-login-password | docker login --username AWS --password-stdin "$ECR_ENDPT"
docker build -t "${ECR_ENDPT}/omics:subcell-convert" .
docker push "${ECR_ENDPT}/omics:subcell-convert"
```

**Workflow launch codes.** OpenCell:

```
miniwdl-omics-run convert_opencell_stardist.wdl \
    docker=${ECR_ENDPT}/omics:subcell-convert \
    --role poweromics --output-uri s3://OUR-BUCKET/out/
```

AllenCell:

```
seq 0 255 \
    | awk '{printf("shards=s3://OUR-BUCKET/allencell-sharded/%s/ ",$0)}' \
    | xargs -n 9999 miniwdl-omics-run \
    --role poweromics --output-uri s3://OUR-BUCKET/out/ --storage-capacity 9600 \
    convert_allencell_outer.wdl docker=${ECR_ENDPT}/omics:subcell-convert
```

This more-complicated incantation enumerates the sharded S3 folders we created above to set as the workflow inputs. OpenCell is much smaller, so the WDL can just shard it internally as it starts up.

## Code of Conduct

This project adheres to the Contributor Covenant [code of conduct](https://github.com/chanzuckerberg/.github/blob/master/CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [opensource@chanzuckerberg.com](mailto:opensource@chanzuckerberg.com).

## Reporting Security Issues

If you believe you have found a security issue, please responsibly disclose by contacting us at [security@chanzuckerberg.com](mailto:security@chanzuckerberg.com).
