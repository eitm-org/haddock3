from setuptools import Extension, setup, find_packages

cpp_extensions = [
    Extension(
        "haddock.bin.contact_fcc",
        sources=["haddock3/src/haddock/deps/contact_fcc.cpp"],
        extra_compile_args=["-O2"],
    ),
    Extension(
        "haddock.bin.fast_rmsdmatrix",
        sources=["haddock3/src/haddock/deps/fast-rmsdmatrix.c"],
        extra_compile_args=["-Wall", "-O3", "-march=native", "-std=c99"],
        extra_link_args=["-lm"],
    ),
]


setup(
   name='haddock3',
   version='1.0',
   packages=find_packages(),
   ext_modules=cpp_extensions
)