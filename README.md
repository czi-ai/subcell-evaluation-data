# Data Processing for SubCell Evaluation 

This repo contains the code to process OpenCell data for evaluating the SubCell models. For license and more information about OpenCell data please see https://opencell.czbiohub.org/download.

## Overview

* `convert_opencell_stardist.py` contains the core logic to process OpenCell images. It runs single-threaded on a local directory of TIFF image files, producing a directory of processed PNG image files and a metadata CSV file.
* `metadata/` has scripts and assets for further post-processing the metadata CSV.
* `Dockerfile` specifies a docker image bundling these scripts with their OS and PyPI dependencies.
* `convert_opencell_stardist.wdl` is a WDL workflow to run the dockerized scripts at scale using [AWS HealthOmics](https://aws.amazon.com/healthomics/). So far, a simple scaling approach using [GNU parallel](https://www.gnu.org/software/parallel/ß) on a single large worker node has sufficed; but the WDL/HealthOmics framework enables further horizontal scaling, if needed in the future.

## Running on AWS

The OpenCell input dataset resides in a public S3 bucket, under `s3://czb-opencell/microscopy/raw/` in us-west-2, so we process it there as well.

**AWS setup and building docker.** We will use the [miniwdl-omics-run](https://github.com/miniwdl-ext/miniwdl-omics-run) local command-line tool to initiate the WDL workflow runs. We assume the tool has been installed (`pip3 install miniwdl-omics-run`) and the one-time AWS account setup steps documented there have been completed.

```
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_DEFAULT_REGION=$(aws configure get region)
ECR_ENDPT="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com"

aws ecr get-login-password | docker login --username AWS --password-stdin "$ECR_ENDPT"
docker build -t "${ECR_ENDPT}/omics:subcell-convert" .
docker push "${ECR_ENDPT}/omics:subcell-convert"

miniwdl-omics-run convert_opencell_stardist.wdl \
    docker=${ECR_ENDPT}/omics:subcell-convert \
    --role poweromics --output-uri s3://OUR-BUCKET/out/
```

## Data Processing

The maximum-intensity z-projection images from OpenCell were used. The nuclei were identified with [StardDist](https://stardist.net/) and crops of 256 x 256 pixels were generated centering around each identified nucleus. These images can be found in the `intermediate/` subfolder. 

The cropped images were further resized from the original pixel size of OpenCell images of 0.206349 μm/pixel to 0.0800885 μm/pixel in order to match that of the training data of SubCell, and the images were resized accordingly to be 640 x 640 pixels. These images can be found in the `resized/` subfolder.

## Code of Conduct

This project adheres to the Contributor Covenant [code of conduct](https://github.com/chanzuckerberg/.github/blob/master/CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [opensource@chanzuckerberg.com](mailto:opensource@chanzuckerberg.com).

## Reporting Security Issues

If you believe you have found a security issue, please responsibly disclose by contacting us at [security@chanzuckerberg.com](mailto:security@chanzuckerberg.com).
