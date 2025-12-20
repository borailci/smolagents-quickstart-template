
# Installation

This guide will walk you through the steps to install Agent Lightning and get your environment ready.

## 1. Prerequisites

- Python 3.9 or higher is required.

## 2. Standard Installation

For the most stable experience, we recommend installing Agent Lightning directly from the Python Package Index (PyPI).

Open your terminal and run the following command:

```bash
pip install agentlightning
```

This will download and install the latest official release.

## 3. Nightly Builds

If you want to try out the newest features and improvements before they are officially released, you can install the nightly build from Test PyPI. These versions are less stable and intended for development and testing purposes.

```bash
pip install --upgrade --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ agentlightning
```

## 4. Verifying the Installation

Once the installation is complete, you can verify it by checking the installed version of Agent Lightning. Run the following command in your terminal:

```bash
pip show agentlightning
```

This will display information about the installed package, including the version number. If you see this information, Agent Lightning has been successfully installed.

You are now ready to start building with Agent Lightning! 
