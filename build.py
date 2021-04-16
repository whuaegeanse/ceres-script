# Copyright (c) 2018, ETH Zurich and UNC Chapel Hill.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of ETH Zurich and UNC Chapel Hill nor the names of
#       its contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Author: Johannes L. Schoenberger (jsch-at-demuc-dot-de), whuaegeansea@gmail.com

import os
import sys
import glob
import shutil
import fileinput
import platform
import argparse
import zipfile
import hashlib
import ssl
import requests
import subprocess
import multiprocessing


PLATFORM_IS_WINDOWS = platform.system() == "Windows"
PLATFORM_IS_LINUX = platform.system() == "Linux"
PLATFORM_IS_MAC = platform.system() == "Darwin"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build ceres and its dependencies locally under Windows, "
                    "Mac, and Linux. Note that under Mac and Linux, it is "
                    "usually easier and faster to use the available package "
                    "managers for the dependencies (see documentation). "
                    "However, if you are on a (cluster) system without root "
                    "access, this script might be useful. This script "
                    "downloads the necessary dependencies automatically from "
                    "the Internet. It assumes that CMake are already installed "
                    "on the system. Under Windows you must specify the location "
                    "of these libraries.")
    parser.add_argument("--build_path", required=True)
    parser.add_argument("--ceres_path", required=True,
                        help="The path to the top ceres source folder, which "
                             "contains src/, scripts/, CMakeLists.txt, etc.")
    parser.add_argument("--local_eigen",  action="store_false",
                        help="Whether to use local eigen", default=False)
    parser.add_argument("--eigen_path",
                        help="The path to the top eigen source folder, which "
                        "contains Eigen/, scripts/, CMakeLists.txt, etc.")
    parser.add_argument("--local_gflags",  action="store_false",
                        help="Whether to use local gflags", default=False)
    parser.add_argument("--gflags_path",
                        help="The path to the top gflags source folder, which "
                        "contains src/, cmake/, CMakeLists.txt, etc.")
    parser.add_argument("--local_glog",  action="store_false",
                        help="Whether to use local glog", default=False)
    parser.add_argument("--glog_path",
                        help="The path to the top glog source folder, which "
                        "contains src/, cmake/, CMakeLists.txt, etc.")
    parser.add_argument("--local_suite_sparse",  action="store_false",
                        help="Whether to use local suite-sparse", default=False)
    parser.add_argument("--suite_sparse_path",
                        help="The path to the top suite-sparse source folder, which "
                        "contains SuiteSparse/, cmake/, CMakeLists.txt, etc.")
    parser.add_argument("--with_suite_sparse",
                        dest="with_suite_sparse", action="store_true")
    parser.add_argument("--without_suite_sparse",
                        dest="with_suite_sparse", action="store_false",
                        help="Whether to use SuiteSparse as a sparse solver "
                             "(default with SuiteSparse)")
    parser.add_argument("--with_tests",
                        dest="with_tests", action="store_true")
    parser.add_argument("--without_tests",
                        dest="with_tests", action="store_false",
                        help="Whether to build unit tests")
    parser.add_argument("--build_type", default="Release",
                        help="Build type, e.g., Debug, Release, RelWithDebInfo")
    parser.add_argument("--cmake_generator", default="",
                        help="CMake generator, e.g., Visual Studio 14")
    parser.add_argument("--no_ssl_verification",
                        dest="ssl_verification", action="store_false",
                        help="Whether to disable SSL certificate verification "
                             "while downloading the source code")

    parser.set_defaults(with_suite_sparse=True)
    parser.set_defaults(with_tests=True)
    parser.set_defaults(ssl_verification=True)

    args = parser.parse_args()

    args.build_path = os.path.abspath(args.build_path)
    args.download_path = os.path.join(args.build_path, "__download__")
    args.install_path = os.path.join(args.build_path, "__install__")

    args.cmake_config_args = []
    args.cmake_config_args.append(
        "-DCMAKE_BUILD_TYPE={}".format(args.build_type))
    args.cmake_config_args.append(
        "-DCMAKE_PREFIX_PATH={}".format(args.install_path))
    args.cmake_config_args.append(
        "-DCMAKE_INSTALL_PREFIX={}".format(args.install_path))
    if args.cmake_generator:
        args.cmake_config_args.extend(["-G", args.cmake_generator])
    if PLATFORM_IS_WINDOWS:
        args.cmake_config_args.append(
            "-DCMAKE_GENERATOR_TOOLSET='host=x64'")
        if "Win64" not in args.cmake_generator:
            args.cmake_config_args.append(
                "-DCMAKE_GENERATOR_PLATFORM=x64")

    args.cmake_build_args = ["--"]
    if PLATFORM_IS_WINDOWS:
        # Assuming that the build system is MSVC.
        args.cmake_build_args.append(
            "/maxcpucount:{}".format(multiprocessing.cpu_count()))
    else:
        # Assuming that the build system is Make.
        args.cmake_build_args.append(
            "-j{}".format(multiprocessing.cpu_count()))

    if not args.ssl_verification:
        ssl._create_default_https_context = ssl._create_unverified_context

    return args


def mkdir_if_not_exists(path):
    assert os.path.exists(os.path.dirname(os.path.abspath(path)))
    if not os.path.exists(path):
        os.makedirs(path)


def copy_file_if_not_exists(source, destination):
    if os.path.exists(destination):
        return
    shutil.copyfile(source, destination)


def check_md5_hash(path, md5_hash):
    computed_md5_hash = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            computed_md5_hash.update(chunk)
    computed_md5_hash = computed_md5_hash.hexdigest()
    if md5_hash != computed_md5_hash:
        print("MD5 mismatch for {}: {} == {}".format(
              path, md5_hash, computed_md5_hash))
        sys.exit(1)


def download_zipfile(url, archive_path, unzip_path, md5_hash):
    if not os.path.exists(archive_path):
        r = requests.get(url)
        with open(archive_path, 'wb') as outfile:
            outfile.write(r.content)
    check_md5_hash(archive_path, md5_hash)
    with zipfile.ZipFile(archive_path, "r") as fid:
        fid.extractall(unzip_path)


def build_cmake_project(args, path, extra_config_args=[],
                        extra_build_args=[], cmakelists_path=".."):
    mkdir_if_not_exists(path)

    cmake_command = ["cmake"] \
        + args.cmake_config_args \
        + extra_config_args \
        + [cmakelists_path]
    return_code = subprocess.call(cmake_command, cwd=path)
    if return_code != 0:
        print("Command failed:", " ".join(cmake_command))
        sys.exit(1)

    cmake_command = ["cmake",
                     "--build", ".",
                     "--target", "install",
                     "--config", args.build_type] \
        + args.cmake_build_args \
        + extra_build_args
    return_code = subprocess.call(cmake_command, cwd=path)
    if return_code != 0:
        print("Command failed:", " ".join(cmake_command))
        sys.exit(1)


def build_eigen(args):
    path = os.path.join(args.build_path, "eigen")
    if os.path.exists(path):
        return

    if not args.local_eigen:
        url = "http://gitlab.com/libeigen/eigen/-/archive/3.3.7/eigen-3.3.7.zip"
        archive_path = os.path.join(args.download_path, "eigen-3.3.7.zip")
        download_zipfile(url, archive_path, args.build_path,
                         "888aab45512cc0c734b3e8f60280daba")
        shutil.move(glob.glob(os.path.join(
            args.build_path, "eigen-*"))[0], path)

        build_cmake_project(args, os.path.join(path, "__build__"))
    else:
        if not os.path.exists(args.eigen_path):
            return
        build_cmake_project(args, os.path.join(
            path, "__build__"), cmakelists_path=os.path.abspath(args.eigen_path))


def build_gflags(args):
    path = os.path.join(args.build_path, "gflags")
    if os.path.exists(path):
        return

    if not args.local_gflags:
        url = "https://github.com/gflags/gflags/archive/v2.2.2.zip"
        archive_path = os.path.join(args.download_path, "gflags-2.2.2.zip")
        download_zipfile(url, archive_path, args.build_path,
                         "ff856ff64757f1381f7da260f79ba79b")
        shutil.move(os.path.join(args.build_path, "gflags-2.2.2"), path)
        os.remove(os.path.join(path, "BUILD"))

        build_cmake_project(args, os.path.join(path, "__build__"))
    else:
        if not os.path.exists(args.gflags_path):
            return
        build_cmake_project(args, os.path.join(
            path, "__build__"), cmakelists_path=os.path.abspath(args.gflags_path))


def build_glog(args):
    path = os.path.join(args.build_path, "glog")
    if os.path.exists(path):
        return

    if not args.local_glog:
        url = "https://github.com/google/glog/archive/v0.3.5.zip"
        archive_path = os.path.join(args.download_path, "glog-0.3.5.zip")
        download_zipfile(url, archive_path, args.build_path,
                         "454766d0124951091c95bad33dafeacd")
        shutil.move(os.path.join(args.build_path, "glog-0.3.5"), path)

        build_cmake_project(args, os.path.join(path, "__build__"))
    else:
        if not os.path.exists(args.glog_path):
            return
        build_cmake_project(args, os.path.join(
            path, "__build__"), cmakelists_path=os.path.abspath(args.glog_path))


def build_suite_sparse(args):
    if not args.with_suite_sparse:
        return

    path = os.path.join(args.build_path, "suite-sparse")
    if os.path.exists(path):
        return

    if not args.local_suite_sparse:
        url = "https://github.com/jlblancoc/" \
              "suitesparse-metis-for-windows/archive/" \
              "master.zip"
        archive_path = os.path.join(args.download_path, "suite-sparse.zip")
        download_zipfile(url, archive_path, args.build_path,
                         "ae3a8d7ce9e461ac2beab352a8f50893")
        shutil.move(os.path.join(args.build_path,
                                 "suitesparse-metis-for-windows-master"), path)

        build_cmake_project(args, os.path.join(path, "__build__"))
    else:
        if not os.path.exists(args.suite_sparse_path):
            return
        build_cmake_project(args, os.path.join(
            path, "__build__"), cmakelists_path=os.path.abspath(args.suite_sparse_path))

    if PLATFORM_IS_WINDOWS:
        lapack_blas_path = os.path.join(path, "lapack_windows/x64/*")
        mkdir_if_not_exists(os.path.join(args.install_path, "lib64"))
        mkdir_if_not_exists(os.path.join(args.install_path,
                                         "lib64/lapack_blas_windows"))
        for library_path in glob.glob(lapack_blas_path):
            copy_file_if_not_exists(
                library_path, os.path.join(args.install_path,
                                           "lib64/lapack_blas_windows",
                                           os.path.basename(library_path)))


def build_ceres_solver(args):
    if not os.path.exists(args.ceres_path):
        return

    path = os.path.join(args.build_path, "ceres")
    mkdir_if_not_exists(path)

    extra_config_args = [
        "-DBUILD_TESTING=OFF",
        "-DBUILD_EXAMPLES=OFF",
    ]

    if args.with_suite_sparse:
        extra_config_args.extend([
            "-DLAPACK=ON",
            "-DSUITESPARSE=ON",
        ])
        if PLATFORM_IS_WINDOWS:
            extra_config_args.extend([
                "-DLAPACK_LIBRARIES={}".format(
                    os.path.join(args.install_path,
                                 "lib64/lapack_blas_windows/liblapack.lib")),
                "-DBLAS_LIBRARIES={}".format(
                    os.path.join(args.install_path,
                                 "lib64/lapack_blas_windows/libblas.lib")),
            ])

    if PLATFORM_IS_WINDOWS:
        extra_config_args.append("-DCMAKE_CXX_FLAGS=/DGOOGLE_GLOG_DLL_DECL=")

    build_cmake_project(args, os.path.join(path, "__build__"),
                        extra_config_args=extra_config_args,
                        cmakelists_path=os.path.abspath(args.ceres_path))


def build_post_process(args):
    if PLATFORM_IS_WINDOWS:
        lapack_paths = glob.glob(
            os.path.join(args.install_path, "lib64/lapack_blas_windows/*.dll"))
        if lapack_paths:
            for lapack_path in lapack_paths:
                copy_file_if_not_exists(
                    lapack_path,
                    os.path.join(
                        args.install_path, "lib",
                        os.path.basename(lapack_path)))


def main():
    args = parse_args()

    mkdir_if_not_exists(args.build_path)
    mkdir_if_not_exists(args.download_path)
    mkdir_if_not_exists(args.install_path)
    mkdir_if_not_exists(os.path.join(args.install_path, "include"))
    mkdir_if_not_exists(os.path.join(args.install_path, "bin"))
    mkdir_if_not_exists(os.path.join(args.install_path, "lib"))
    mkdir_if_not_exists(os.path.join(args.install_path, "share"))

    build_eigen(args)
    build_gflags(args)
    build_glog(args)
    build_suite_sparse(args)
    build_ceres_solver(args)
    build_post_process(args)

    print()
    print()
    print("Successfully installed ceres in: {}".format(args.install_path))


if __name__ == "__main__":
    main()
