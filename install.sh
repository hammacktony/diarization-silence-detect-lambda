#  Download ffmpeg
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz

# Extract tar
tar -xJf ffmpeg-release-amd64-static.tar.xz

# Make python.zip for Lambda
mkdir python
cp ffmpeg-4.3.1-amd64-static/ffmpeg python/  # Version number might change
chmod u+x python/ffmpeg
zip -r python.zip python/