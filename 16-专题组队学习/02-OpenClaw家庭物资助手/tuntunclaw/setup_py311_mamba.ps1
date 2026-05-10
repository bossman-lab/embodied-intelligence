param(
    [string]$EnvName = "vlm_grasp311",
    [string]$ProjectRoot = "C:\\oc\\VLM_Grasp_Interactive"
)

$ErrorActionPreference = "Stop"

function Resolve-Mamba {
    if (Get-Command mamba -ErrorAction SilentlyContinue) { return "mamba" }
    if (Get-Command micromamba -ErrorAction SilentlyContinue) { return "micromamba" }
    throw "Neither mamba nor micromamba is available in PATH."
}

$mambaExe = Resolve-Mamba
Write-Host "Using: $mambaExe"

Push-Location $ProjectRoot
try {
    $env:PYTHONNOUSERSITE = "1"
    & $mambaExe create -n $EnvName python=3.11 pip cmake ninja -y
    & $mambaExe run -n $EnvName python -m pip install -r requirements-py311.txt
    # Hard-lock critical ABI-sensitive packages to avoid NumPy 2.x binary mismatch.
    & $mambaExe run -n $EnvName python -m pip install --force-reinstall --no-deps `
        numpy==1.26.4 scipy==1.16.0 matplotlib==3.10.6 pillow==11.3.0 roboticstoolbox-python==1.1.1

    Push-Location "$ProjectRoot\graspnet-baseline\pointnet2"
    try {
        & $mambaExe run -n $EnvName python setup.py install
    }
    finally {
        Pop-Location
    }

    & $mambaExe run -n $EnvName python -c "import numpy,scipy,roboticstoolbox; print('numpy',numpy.__version__); print('scipy',scipy.__version__); print('rtb',roboticstoolbox.__version__)"

    Write-Host "Install completed for env: $EnvName"
    Write-Host "Run: $mambaExe run -n $EnvName python main_openclaw.py"
}
finally {
    Pop-Location
}
