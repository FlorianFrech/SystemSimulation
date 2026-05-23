\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{tuw-thesis}[2025/03/22 TUW Thesis Class]

% Pass standard options to the base class
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{report}}


% Feature options
\newif\ifcolorhyperref
\newif\ifusedraftmode
\newif\ifuseshorttoc

% Set the twoside option manually
\DeclareOption{oneside}{\PassOptionsToClass{oneside}{report}}
\DeclareOption{twoside}{\PassOptionsToClass{twoside}{report}}

% Default settings
\DeclareOption{colorlinks}{\colorhyperreftrue}
\DeclareOption{bwlinks}{\colorhyperreffalse}
\DeclareOption{draftmode}{\usedraftmodetrue}
\DeclareOption{shorttoc}{\useshorttoctrue}

% Process options before loading the base class
\ProcessOptions\relax

% For ifdefstring
\RequirePackage{etoolbox}

% Define thesis metadata with defaults
\newcommand{\thesiscaption}{MASTER'S THESIS}
\newcommand{\thesistitle}{Default Title}
\newcommand{\thesisauthor}{Default Author}
\newcommand{\thesissupervisor}{Default Supervisor}
\newcommand{\thesiscollaborator}{} % Empty by default
\newcommand{\thesisdate}{\today}
\newcommand{\thesisdegree}{Master of Science}
\newcommand{\thesisprogram}{Computational Science and Engineering}
\newcommand{\thesisinstitute}{Institute for Theoretical Physics}
\newcommand{\thesisuniversity}{Vienna University of Technology}
\newcommand{\thesisunilogo}{}
\newcommand{\thesisinstlogo}{} % Empty by default

\DeclareRobustCommand{\setthesiscaption}[1]{\renewcommand{\thesiscaption}{#1}}
\DeclareRobustCommand{\setthesistitle}[1]{\renewcommand{\thesistitle}{#1}}
\DeclareRobustCommand{\setthesisauthor}[1]{\renewcommand{\thesisauthor}{#1}}
\DeclareRobustCommand{\setthesissupervisor}[1]{\renewcommand{\thesissupervisor}{#1}}
\DeclareRobustCommand{\setthesiscollaborator}[1]{\renewcommand{\thesiscollaborator}{#1}}
\DeclareRobustCommand{\setthesisdate}[1]{\renewcommand{\thesisdate}{#1}}
\DeclareRobustCommand{\setthesisdegree}[1]{\renewcommand{\thesisdegree}{#1}}
\DeclareRobustCommand{\setthesisprogram}[1]{\renewcommand{\thesisprogram}{#1}}
\DeclareRobustCommand{\setthesisinstitute}[1]{\renewcommand{\thesisinstitute}{#1}}
\DeclareRobustCommand{\setthesisuniversity}[1]{\renewcommand{\thesisuniversity}{#1}}
\DeclareRobustCommand{\setthesisunilogo}[1]{\renewcommand{\thesisunilogo}{#1}}
\DeclareRobustCommand{\setthesisinstlogo}[1]{\renewcommand{\thesisinstlogo}{#1}}

% Title Page Command
\newcommand{\maketitlepage}{
\begin{titlepage}
    \centering
    
    % Logo handling
    \ifdefstring{\thesisinstlogo}{}{
        \includegraphics[height=4cm]{\thesisunilogo} \\
    }{
        \begin{figure}[h]
        \centering
            \begin{subfigure}{.49\textwidth}
                \flushleft
                \includegraphics[height=3cm]{\thesisunilogo} \\
            \end{subfigure}
            \begin{subfigure}{.49\textwidth}
                \flushright
                \includegraphics[height=3cm]{\thesisinstlogo} \\
            \end{subfigure}
        \end{figure}
    }
    
    \vspace{1.25cm}
    {\huge \thesiscaption} \\
    \vspace{1.25cm}
    {\LARGE \textbf{\thesistitle} \par}
    \vspace{1.25cm}
    {\large In fulfillment of the requirements for the academic degree} \\
    \vspace{0.3cm}
    {\Large \textbf{\thesisdegree}} \\
    \vspace{0.3cm}
    {\large as part of the study program} \\
    \vspace{0.3cm}
    {\Large \textbf{\thesisprogram}} \\
    \vspace{0.3cm}
    {\large submitted by} \\
    \vspace{0.3cm}
    {\Large \thesisauthor} \\
    \vspace{1cm}
    {\large carried out at the \thesisinstitute \\ at the \thesisuniversity} \\
    \vspace{1cm}
    {\large under supervision of \\ \thesissupervisor} \\

    % Check if a collaborator is provided
    \ifdefstring{\thesiscollaborator}{}{}{
            {\large and with collaboration of \\ \thesiscollaborator} \\
        }

    \vspace{1cm}
    {\Large \thesisdate}
\end{titlepage}
}

% Default document class settings
\LoadClass{report} 

% Required Packages
\RequirePackage{hyperref}
\RequirePackage{fancyhdr}
\RequirePackage{titlesec}
\RequirePackage{setspace}
\RequirePackage{lineno}
\RequirePackage[toc]{appendix}
\RequirePackage{xcolor}
\RequirePackage{listings}
\RequirePackage{booktabs}
\RequirePackage{array}
\RequirePackage{longtable}
\RequirePackage{graphicx}
\RequirePackage{enumitem}

% Encoding and Language
\RequirePackage[T1]{fontenc}
\RequirePackage[utf8]{inputenc}
\RequirePackage[english]{babel}

% Bibliography
%\RequirePackage[backend=biber, style=chem-angew, articletitle=true]{biblatex}
\RequirePackage[
  backend=biber,
  %style=ieee,
  style=numeric-comp,
  sorting=none,
  giveninits=true,
  doi=true,
  url=false,
  isbn=false
]{biblatex}
\addbibresource{references.bib}
\RequirePackage{csquotes}

% Define TUW color
\definecolor{tuw-color}{HTML}{006699}

% Define general listing style
\lstset{
    basicstyle=\ttfamily\footnotesize,       % Font style and size for the code
    keywordstyle=\color{blue}\bfseries,      % Keywords in blue and bold
    commentstyle=\color{green!50!black}\itshape, % Comments in green and italic
    stringstyle=\color{red},                 % Strings in red
    numbers=left,                           % Line numbers on the left
    numberstyle=\tiny,                      % Line numbers in smaller font
    stepnumber=1,                           % Line numbers for each line
    numbersep=5pt,                          % Space between line numbers and code
    breaklines=true,                        % Automatically break long lines
    frame=tb,                               % Frame at top and bottom of code
    tabsize=4,                              % Tab size (for 4 spaces)
    captionpos=b,                           % Caption position at the bottom
    showstringspaces=false,                 % Do not show spaces in strings
    backgroundcolor=\color{tuw-color!5!white},    % Background color (optional)
    extendedchars=true,                     % Use extended characters
}

% For C++ specific settings
\lstdefinestyle{cpp}{
    language=C++,                            % Set language to C++
    morekeywords={nullptr, override, final, typedef, template, class, public, private, protected, namespace}, % Additional C++ keywords
    otherkeywords={int, double, float, char, bool}, % Data types
    morecomment=[l]{//},                      % Single-line comments
    morecomment=[s]{/*}{*/},                  % Multi-line comments
    morestring=[b]"                         % Strings enclosed by double quotes
}

% For Python specific settings
\lstdefinestyle{python}{
    language=Python,                         % Set language to Python
    morekeywords={def, return, import, from, as, class, pass, break, continue, lambda, yield}, % Python keywords
    commentstyle=\color{green!50!black}\itshape, % Comments in green and italic
    stringstyle=\color{red},                 % Strings in red
    morestring=[b]",                         % Strings enclosed by double quotes
}

% For Modelica specific settings
\lstdefinelanguage{Modelica}{
    morekeywords={model, end, parameter, constant, equation, initial, algorithm,
                  when, then, if, else, elseif, for, while, connect, der,
                  Real, Integer, Boolean, String, input, output, protected,
                  public, partial, extends, within, reinit, annotation},
    morecomment=[l]{//},
    morecomment=[s]{/*}{*/},
    morestring=[b]",
    sensitive=true,
}

\lstdefinestyle{modelica}{
    language=Modelica,
    commentstyle=\color{green!50!black}\itshape,
    stringstyle=\color{red},
}


% Paragraph settings
\setlength{\parindent}{1.5em}
\setlength{\parskip}{0pt}
\setstretch{1.15}

% Fancy Header/Footer
\pagestyle{fancy}
\fancyhf{}
\setlength{\headheight}{14.5pt}

% Set up the header rule and page layout based on one-sided or two-sided mode
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0pt}
\renewcommand{\headwidth}{\textwidth}

\titleformat{\chapter}[block]
    {\normalfont\huge\bfseries}  % Large bold text
    {\hfill\textcolor{tuw-color}{\textsc{\chaptername\ \thechapter}}} % "Chapter X" flush right
    {0pt}  % No extra spacing
    {\Huge\flushright}  % Chapter title is right-aligned
    [\vspace{-3.5ex}\titlerule\vspace{3ex}]  % Insert ruler after the chapter number


\renewcommand{\chaptermark}[1]{%
  \markboth{\thechapter\ #1}{}
}

\renewcommand{\sectionmark}[1]{%
  \markright{\thesection\ #1}
}

% Custom header for one-sided layout (chapter or section based on content)
\if@twoside
    \fancyhead[LE]{\nouppercase{\leftmark}}  % Chapter on left even pages
    \fancyhead[RO]{\nouppercase{\rightmark}}  % Section on right odd pages
    \fancyfoot[LE]{\thepage}   % Left footer on even pages
    \fancyfoot[RO]{\thepage}   % Right footer on odd pages
\else
    % Header content for one-sided layout (chapter or section based on content)
    \fancyhead[R]{%
      \ifnum \value{section}=0
        \nouppercase{\leftmark}  % Show chapter name if no section
      \else
        \nouppercase{\rightmark} % Show section number and name
      \fi}
    \fancyfoot[C]{\thepage}
\fi

% Define frontmatter and mainmatter
\newcommand{\frontmatter}{
  \cleardoublepage
  \setcounter{page}{1}  % Reset page number to I (Roman numerals)
  \renewcommand{\thepage}{\Roman{page}}  % Roman numbering for frontmatter
}

\newcommand{\mainmatter}{
  \cleardoublepage
  \setcounter{page}{1}  % Reset page number to 1 (Arabic numerals)
  \renewcommand{\thepage}{\arabic{page}}  % Arabic numbering for mainmatter
  \setcounter{chapter}{0}  % Enable chapter numbering
}

% Draft Mode
\ifusedraftmode
  \overfullrule=5pt
  \linenumbers
\fi

% Table of Contents Depth Control
\ifuseshorttoc
  \setcounter{tocdepth}{1} % Show only chapters & sections
\fi

% Appendix setup
\newcommand{\appendixsetup}{%
    \renewcommand{\chaptername}{Appendix}
    \renewcommand{\thechapter}{\Alph{chapter}}
}

\renewcommand{\appendix}{%
    \renewcommand{\theHchapter}{A\arabic{chapter}}
    \clearpage
    \appendixsetup
    \setcounter{chapter}{0} % Reset chapter counter
}

% Hyperref Color Settings
% \ifcolorhyperref
%     \hypersetup{colorlinks=false, linkcolor=violet, citecolor=green, urlcolor=blue}
% \else
%     \hypersetup{colorlinks=true, linkcolor=black, citecolor=black, urlcolor=black}
% \fi
% Hyperref Color Settings
\ifcolorhyperref
    \hypersetup{
        colorlinks=true,
        linkcolor=tuw-color!65!black,
        citecolor=tuw-color!65!black,
        urlcolor=tuw-color!65!black
    }
\else
    \hypersetup{
        colorlinks=true,
        linkcolor=black,
        citecolor=black,
        urlcolor=black
    }
\fi

\endinput
