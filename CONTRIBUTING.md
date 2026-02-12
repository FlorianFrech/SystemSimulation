# Contributing

Thanks for considering a contribution!

## License for contributions

By submitting a pull request, you agree that your contribution is licensed under the same terms as
this repository's license (**MIT**, see `LICENSE`).

## Jupyter Widget State For Docs (JupyterLab Required)

Some tutorials embed interactive `ipywidgets` (e.g., NGSolve `webgui` scenes). To keep these
interactive in the built documentation, the notebook must **save widget state**. VS Code does not
reliably persist widget state into `.ipynb`, so use **JupyterLab** for this step.

Steps:
1. Launch JupyterLab from the repo root.
2. Open the tutorial notebook and run the cells that create widgets (e.g., `Draw(...)`).
3. Enable `Settings → Save Widget State Automatically`.
4. Save the notebook.

If the `jpserver-...-open.html` file cannot be opened due to sandboxing, open the `http://127.0.0.1:8888/lab?...`
URL printed in the terminal instead.
