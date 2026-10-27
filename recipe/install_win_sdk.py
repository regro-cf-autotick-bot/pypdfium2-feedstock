"""
Provisions the exact Windows SDK version pinned by PDFium's vendored build
system (build/vs_toolchain.py, build/toolchain/win/setup_toolchain.py) for the
toolchained sourcebuild on Windows. That pin currently points at an
early-release SDK (10.0.28000.0) that is not preinstalled on standard CI
runners. Microsoft distributes it as NuGet packages (used by MSBuild/CMake
pipelines that need a specific SDK without the GUI installer); this script
downloads the relevant subset and lays the files out under the conventional
"C:\\Program Files (x86)\\Windows Kits\\10" tree, which is what vcvarsall.bat's
own filesystem-based SDK lookup expects, so the toolchained build's default,
unpatched logic finds everything it looks for on disk.
"""

import os
import shutil
import tempfile
import urllib.request
import zipfile

SDK_VERSION = "10.0.28000.0"
NUGET_VERSION = "10.0.28000.2270"
KITS_ROOT = r"C:\Program Files (x86)\Windows Kits\10"

# (nuget package, package version) -> list of (path inside package, destination)
PACKAGES = {
    "microsoft.windows.sdk.cpp": [
        (f"c/Include/{SDK_VERSION}", os.path.join(KITS_ROOT, "Include", SDK_VERSION)),
        (f"c/bin/{SDK_VERSION}/x64", os.path.join(KITS_ROOT, "bin", SDK_VERSION, "x64")),
    ],
    "microsoft.windows.sdk.cpp.x64": [
        ("c/um/x64", os.path.join(KITS_ROOT, "Lib", SDK_VERSION, "um", "x64")),
        ("c/ucrt/x64", os.path.join(KITS_ROOT, "Lib", SDK_VERSION, "ucrt", "x64")),
        ("c/ucrt_enclave/x64", os.path.join(KITS_ROOT, "Lib", SDK_VERSION, "ucrt_enclave", "x64")),
    ],
    # GN bootstraps toolchain environments for multiple host CPUs (e.g. x86) even
    # when only building for x64, so the x86 SDK libs must exist too, or `gn gen`
    # fails validating environment.x86 before any actual x86 compilation happens.
    "microsoft.windows.sdk.cpp.x86": [
        ("c/um/x86", os.path.join(KITS_ROOT, "Lib", SDK_VERSION, "um", "x86")),
        ("c/ucrt/x86", os.path.join(KITS_ROOT, "Lib", SDK_VERSION, "ucrt", "x86")),
    ],
}

NUGET_URL = "https://api.nuget.org/v3-flatcontainer/{pkg}/{ver}/{pkg}.{ver}.nupkg"


def main():
    marker = os.path.join(KITS_ROOT, "Include", SDK_VERSION, "shared", "sdkddkver.h")
    if os.path.exists(marker):
        print(f"Windows SDK {SDK_VERSION} already present, skipping install.")
        return

    with tempfile.TemporaryDirectory() as tmp:
        for pkg, mappings in PACKAGES.items():
            url = NUGET_URL.format(pkg=pkg, ver=NUGET_VERSION)
            nupkg_path = os.path.join(tmp, f"{pkg}.nupkg")
            print(f"Downloading {url} ...")
            urllib.request.urlretrieve(url, nupkg_path)

            extract_dir = os.path.join(tmp, pkg)
            with zipfile.ZipFile(nupkg_path) as zf:
                zf.extractall(extract_dir)

            for src_rel, dst in mappings:
                src = os.path.join(extract_dir, *src_rel.split("/"))
                print(f"Installing {src_rel} -> {dst}")
                shutil.copytree(src, dst, dirs_exist_ok=True)

    if not os.path.exists(marker):
        raise SystemExit(f"Windows SDK install did not produce expected file: {marker}")
    print(f"Windows SDK {SDK_VERSION} installed successfully.")


if __name__ == "__main__":
    main()
