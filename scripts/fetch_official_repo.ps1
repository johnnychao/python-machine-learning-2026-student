$ErrorActionPreference = 'Stop'
$target = Join-Path $PSScriptRoot '..\notebooks\official_source'
if (-not (Test-Path $target)) {
  git clone --depth 1 https://github.com/rasbt/python-machine-learning-book-3rd-edition.git $target
} else {
  git -C $target pull --ff-only
}
