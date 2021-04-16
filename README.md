ceres-script
============

About
-----
ceres-script is a python script to build (ceres solver)[https://github.com/ceres-solver/ceres-solver], simple and
easy to use, especially on Windows platform.

Building ceres solver on the Windows platform is a very troublesome task, because it relies on third-party libraries
such as glog, gflag, eigen, lapack, blas, suitespare and so on. It may take several hours to download and configure
these third-party libraries. The foundation of this project comes from the build script of colmap, which greatly
reduces the difficulty of building on the windows platform. On the basis of the colmap build script, this project
adds support for local glog, gflag, eigen, suitespare and other third-party libraries. In other words, users can
specify a local third-party library instead of a fixed version downloaded from the Internet. This will help the
third-party library that ceres solver relies on to be consistent with the third-party library used locally by user.

How to use
----------
1. Install cmake, python 3.5+.
2. Install Requests via pip($ python -m pip install requests).
3. Run the following script from shell or cmd.
```
    python D:\ThirdLibs\ceres-solver\build.py --build_path D:\ThirdLibs\ceres-solver\ceres-solver-build --ceres_path 
    D:\ThirdLibs\ceres-solver\ceres-solver --with_suite_sparse --no_ssl_verification --cmake_generator 
    "Visual Studio 15 2017" --no_ssl_verification 
```

Acknowledgments
---------------

Thanks to Johannes L. Schoenberger, the author of colmap, for providing such
a great open source SfM-MVS library. The foundation of this project comes
from the build script of colmap.


License
-------

The ceres-script library is licensed under the new BSD license. Note that this text
refers only to the license for ceres-script itself, independent of its dependencies,
which are separately licensed. Building ceres-script with these dependencies may
affect the resulting ceres-script license.
```
    Copyright (c) 2018, ETH Zurich and UNC Chapel Hill.
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

        * Redistributions of source code must retain the above copyright
          notice, this list of conditions and the following disclaimer.

        * Redistributions in binary form must reproduce the above copyright
          notice, this list of conditions and the following disclaimer in the
          documentation and/or other materials provided with the distribution.

        * Neither the name of ETH Zurich and UNC Chapel Hill nor the names of
          its contributors may be used to endorse or promote products derived
          from this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
    AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
    ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE
    LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
    CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.

    Author: Johannes L. Schoenberger (jsch-at-demuc-dot-de), whuaegeansea@gmail.com
```