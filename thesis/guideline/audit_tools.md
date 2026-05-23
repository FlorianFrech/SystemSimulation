<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# I am writing a thesis about a Python framework for heterogeneous hybrid co-simulation with FMI, OpenSim, FEM/NGSolve, algebraic-loop handling, event localization, and runtime model switching.

Check whether the following related-work/tool-comparison section misses important current open-source tools or makes inaccurate claims. Focus on FMI co-simulation, Python digital twin frameworks, FEM toolchains, and multi-fidelity simulation.

Return:

- missing tools or references,
- inaccurate claims,
- citations I should add,
- claims that are too strong.

Your section is broadly on the right track, but it misses a few current open-source tools and a couple of claims should be softened. The most important additions are FMI 3.0-capable Python tooling, a few Python digital-twin/co-simulation frameworks, and more explicit FEM alternatives beyond NGSolve.[^1][^2][^3][^4][^5][^6]

## Missing tools or references

- **FMPy** should be explicitly cited as a current open-source Python FMU tool, because it supports FMI 1.0, 2.0, and 3.0, including Co-Simulation and Model Exchange.[^1]
- **PyFMI** is still worth citing as a classic Python FMU interface, especially if you contrast older and newer Python FMU stacks; it supports FMU loading and simulation from Python.[^7]
- **CoFMPy** is a relevant recent Python framework for FMI-based digital twins and co-simulation, so it is a good addition if your related work discusses Python orchestration layers.[^8]
- **MultiCoSim** is another recent Python-based multi-fidelity co-simulation framework and fits your “runtime model switching / heterogeneous orchestration” angle well.[^3]
- For **FEM toolchains**, add **FEniCSx/FEniCS** and possibly **deal.II** or **FreeFEM** as open-source comparators, since they are established open-source FEM ecosystems with Python-facing workflows or interfaces.[^4][^5][^6]
- For **OpenSim + Python**, cite OpenSim’s Python wrapping/documentation rather than treating Python support as an external add-on; OpenSim does provide Python API access.[^9]


## Inaccurate or weak claims

- The claim that **“direct FMU export remains uncommon”** is too strong unless you scope it to your exact use case. FMUs are widely used for co-simulation, and FMI 3.0 explicitly expands support for events, clocks, scheduled execution, and intermediate variable access.[^2][^1]
- If you say **FMI is the central basis for co-simulation workflows across tools**, that is defensible, but it should be framed as “widely used” rather than universal, because many toolchains still rely on tool-specific wrappers or native APIs.[^7][^9][^1]
- The statement that **OpenSim models usually require tool-specific integration in co-simulation** is plausible, but it should be softened unless you cite it carefully; OpenSim has a Python API, so “tool-specific integration” should not imply lack of scripting or automation support.[^9]
- The phrase **“FEM models are usually integrated through custom wrappers or tool-specific interfaces”** is too broad. It is true for your thesis context, but FEM ecosystems such as NGSolve, FEniCSx, and deal.II all provide strong scripting or Python integration paths.[^10][^5][^4]


## Claims that are too strong

| Current claim | Safer wording |
| :-- | :-- |
| “Direct FMU export remains uncommon.” | “Direct FMU export is less common for some specialized model classes, especially where custom state transfer or solver control is needed.” [^2][^1] |
| “FMI-based coupling is enough for heterogeneous models.” | “FMI-based coupling is a common basis, but specialized wrappers or orchestration logic are often still needed for hybrid events, algebraic loops, and runtime switching.” [^2][^8] |
| “OpenSim models usually require tool-specific integration.” | “OpenSim models are often integrated via OpenSim’s API or custom wrappers, depending on the co-simulation workflow.” [^9] |
| “FEM models are integrated through custom wrappers.” | “In the thesis context, FEM models often need custom wrappers, although some FEM ecosystems also offer Python-native workflows.” [^10][^4][^5] |

## Citations to add

Add citations at the points where you describe each tool class:

- FMPy as a Python FMU library with FMI 1.0/2.0/3.0 support.[^1]
- PyFMI as a Python FMU loader/simulator.[^7]
- FMI 3.0 features such as clocks, scheduled execution, early return, and event mode.[^2]
- OpenSim Python scripting/API support.[^9]
- NGSolve’s Python interface.[^10]
- FEniCSx / FEniCS as open-source FEM/Python ecosystems.[^11][^4]
- deal.II and FreeFEM as additional open-source FEM references.[^5][^6]
- CoFMPy and MultiCoSim as recent Python co-simulation/digital-twin frameworks.[^3][^8]


## What I would revise

I would make your related-work section explicitly distinguish these buckets:

1. **FMI / FMU Python tooling**: FMPy, PyFMI, CoFMPy.[^8][^1][^7]
2. **Python digital-twin / co-simulation orchestration**: MultiCoSim, CoFMPy, and any framework that handles orchestration rather than just FMU loading.[^3][^8]
3. **OpenSim integration**: OpenSim Python API, not just OpenSim as a standalone biomechanics platform.[^9]
4. **FEM toolchains**: NGSolve, FEniCSx, deal.II, FreeFEM.[^6][^4][^5][^10]
5. **FMI 3.0 gap**: note that your implementation uses FMI 2.0 Co-Simulation, so features like clocks and scheduled execution are beyond the current thesis scope.[^2]

I can also turn this into a **thesis-ready redline**: a list of exact sentences from your section that should be rewritten, with replacement wording and citations.
<span style="display:none">[^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^30]</span>

<div align="center">⁂</div>

[^1]: https://github.com/CATIA-Systems/FMPy

[^2]: https://fmi-standard.org/faq/

[^3]: https://arxiv.org/abs/2506.10869

[^4]: https://fenicsproject.org

[^5]: https://www.dealii.org

[^6]: https://freefem.org

[^7]: https://github.com/modelon-community/PyFMI/blob/master/doc/sphinx/source/tutorial.rst

[^8]: https://conf.researchr.org/details/edtconf-2025/edtconf-2025-papers/15/CoFMPy-A-Python-Framework-for-Rapid-Prototyping-of-FMI-based-Digital-Twins

[^9]: https://opensimconfluence.atlassian.net/wiki/spaces/OpenSim33/pages/53674144/Scripting+in+Python

[^10]: https://docu.ngsolve.org/latest/

[^11]: https://github.com/fenics

[^12]: main.pdf

[^13]: https://openmodelica.org/doc/OpenModelicaUsersGuide/v1.12.0/omsimulator.html

[^14]: https://openmodelica.org/doc/OpenModelicaUsersGuide/latest/fmitlm.html

[^15]: https://openmodelica.org/doc/OpenModelicaUsersGuide/v1.11.0/fmi.html

[^16]: https://openmodelica.org/doc/OpenModelicaUsersGuide/v1.15.0/fmitlm.html

[^17]: https://fmpy.readthedocs.io

[^18]: https://stackoverflow.com/questions/54019129/fmu-module-and-transfer-from-openmodelica-to-python-with-pyfmi

[^19]: https://simtk.org/projects/opengrf

[^20]: https://www.nafems.org/downloads/forum/post1843/fmi_3.0_whats_new.pdf

[^21]: https://github.com/modelica/fmi-standard/issues/1400

[^22]: https://www.youtube.com/watch?v=ZT918VcYVlA

[^23]: https://www.inlibra.com/10.51202/9783181024232-447.pdf

[^24]: https://modelica.github.io/fmi-guides/main/fmi-guide/

[^25]: https://github.com/jonathanritchie/OpenSim-API-Python

[^26]: https://docs.hpc.ethz.ch/software/fenics/

[^27]: https://www.youtube.com/watch?v=cRRlPPLN8ps

[^28]: https://en.wikipedia.org/wiki/FEniCS_Project

[^29]: https://jschoeberl.github.io/talk-pdesoft/talk_pdesoft.html

[^30]: https://gitlab.epfl.ch/napde/napde-exercises-2026/-/blob/main/prologue/fenicsx.md

