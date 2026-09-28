# Launches the standalone prototype from localhost so YouTube receives a valid Referer header.
param([int]$Port = 8787)

$prototypeDirectory = Join-Path $PSScriptRoot '..\output\unga-prototype'
if (-not (Test-Path $prototypeDirectory)) {
    throw "Prototype directory was not found: $prototypeDirectory"
}

py -m http.server $Port --directory $prototypeDirectory
