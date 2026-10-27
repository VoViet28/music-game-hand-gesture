$ErrorActionPreference = "Stop"

try {
    $Version = & python -c "import sys; assert (3, 10) <= sys.version_info[:2] < (3, 13); print('.'.join(map(str, sys.version_info[:3])))" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Python command failed" }
    Write-Host "Dang dung Python $Version"
}
catch {
    Write-Error "Can Python 3.10-3.12 (64-bit). Hay cai tu python.org va bat tuy chon Add Python to PATH."
}

python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Khong tao duoc .venv" }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Khong cap nhat duoc pip" }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Khong cai dat duoc thu vien" }
Write-Host "Cai dat xong. Chay: .\.venv\Scripts\python.exe run_music_game.py"

