from distutils.core import setup

setup(
    name = "Blake",
    version = "0.2.2",
    author = "Karlis Lauva",
    author_email = "karlis@cobookapp.com",
    packages = ["blake"],
    license = "LICENSE.txt",
    description = "Do cool things with your Markdown documents",
    long_description = open("README.txt").read(),
    install_requires = [
        "Markdown >= 2.2.0",
        "PyYAML >= 3.10",
    ]
)
