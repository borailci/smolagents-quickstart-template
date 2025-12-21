# Latex Installation Guide

### 🐧 Linux (Ubuntu/Debian)

Linux users generally have the easiest path via the built-in package manager.

1. **Install the Engine**:
   Open your terminal and install the full distribution to avoid missing package errors:
   
   ```bash
   sudo apt update
   sudo apt install texlive-full latexmk
   ```

2. **Install the IDE**:
   Download and install **Cursor** or **VS Code**.

3. **Configure Extension**:
   
   * Open Cursor/VS Code.
   * Go to the Extensions view (`Ctrl+Shift+X`) and install **LaTeX Workshop**.

4. **Test**:
   Create a `main.tex` file, save it, and the extension will automatically build the PDF in a side-by-side view.

---

### 🪟 Windows (MiKTeX + VS Code)

On Windows, **MiKTeX** is the preferred distribution because it can download missing packages "on the fly."

1. **Install the Engine**:
   * Download the **MiKTeX** installer from [miktex.org](https://miktex.org/download).
   * Run the installer. Choose "Install packages on the fly: **Always**" during setup.
2. **Install Perl** (Required for `latexmk` automation):
   * Install **Strawberry Perl** from [strawberryperl.com](https://strawberryperl.com/).
3. **Install the IDE**:
   Download and install **Cursor** or **VS Code**.
4. **Configure Extension**:
   * In the Extensions view, install **LaTeX Workshop**.
5. **Test**:
   Open a `.tex` file. MiKTeX might pop up a window asking for permission to download packages the first time you compile; click **Install**.

---

### 🍎 macOS (MacTeX + VS Code)

macOS uses a specialized version of TeX Live called MacTeX.

1. **Install the Engine**:
   
   * **Option A (Manual)**: Download the **MacTeX.pkg** (~5GB) from [tug.org/mactex](https://tug.org/mactex/).
   
   * **Option B (Homebrew)**: If you use Homebrew, run:
     
     ```bash
     brew install --cask mactex-no-gui
     ```

2. **Install the IDE**:
   Download and install **Cursor** or **VS Code**.

3. **Configure Extension**:
   
   * In the Extensions view, install **LaTeX Workshop**.

4. **Set Path (If needed)**:
   MacTeX usually adds itself to your path automatically. If compilation fails, ensure `/Library/TeX/texbin` is in your system environment variables.

5. **Test**:
   Open a `.tex` file and press `Cmd+Opt+B` to build.
