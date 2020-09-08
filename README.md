# Noise Detect Lambda Function

`lambda_function.py` is the Python lambda function for noise detect. It depends on `ffmpeg`. This is installed at `/opt/python/ffmpeg` in AWS.

# Install

## FFMPEG
To get FFMPEG installed, run install. This will download dependencies necesssary and create a `python.zip` to be uploaded as an AWS Lambda Layer.

## AWS Lambda
+ Create a new Lambda function
+ Copy the Lambda function into the function pane
+ Create new layer and upload `python.zip`
+ Configure Lambda to use this layer
+ Create REST ingress point

# Data

## Example of input data

```json
{
    "body": {
        "bucket_name": "bucket",
        "key_name": "file.mkv",
        "noise_tolerance": -36,
        "noise_duration": 0.3
    }
}
```

## Example of what the lambda returns
```json
{
  "statusCode": 200,
  "data": {
    "success": true,
    "noise_detected": true,
    "error": null
  }
}
```