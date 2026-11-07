# Third-party notices

Mouse Plus is licensed under the [GNU General Public License v3.0](LICENSE).
It is built on the open-source components below. The released `MousePlus.exe` contains all of them; running from source only needs them installed (see `requirements.txt`).

| Component | Version | License | Source |
| --- | --- | --- | --- |
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | 6.11.0 | GPL-3.0 | <https://pypi.org/project/PyQt6/> |
| [Qt 6](https://www.qt.io/) (via PyQt6-Qt6) | 6.11.2 | LGPL-3.0 | <https://download.qt.io/official_releases/qt/> |
| [PyQt6-sip](https://pypi.org/project/PyQt6-sip/) | 13.12.0 | BSD-2-Clause | <https://pypi.org/project/PyQt6-sip/> |
| [PyQt6-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) | 1.11.3 | GPL-3.0 | <https://github.com/zhiyiYo/PyQt-Fluent-Widgets> |
| [PyQt6-Frameless-Window](https://github.com/zhiyiYo/PyQt-Frameless-Window) | 0.8.2 | GPL-3.0 | <https://github.com/zhiyiYo/PyQt-Frameless-Window> |
| [darkdetect](https://github.com/albertosottile/darkdetect) | 0.8.0 | BSD-3-Clause | <https://github.com/albertosottile/darkdetect> |
| [pywin32](https://github.com/mhammond/pywin32) | 312 | BSD-3-Clause style | <https://github.com/mhammond/pywin32> |
| [Python](https://www.python.org/) | 3.12 | PSF License Agreement | <https://www.python.org/downloads/source/> |
| [PyInstaller](https://pyinstaller.org/) bootloader | 6.22.3 | GPL-2.0-or-later with Bootloader Exception | <https://github.com/pyinstaller/pyinstaller> |

The versions are the ones used to build the exe.

## GPL-3.0 components

PyQt6 is Copyright (c) Riverbank Computing Limited. PyQt6-Fluent-Widgets and PyQt6-Frameless-Window are Copyright (c) zhiyiYo.
They are used under the GNU General Public License v3.0, the same license as Mouse Plus; its full text is in [LICENSE](LICENSE).

## Qt (LGPL-3.0)

The exe contains the Qt 6 libraries, Copyright (c) The Qt Company Ltd. and other contributors, used under the
[GNU Lesser General Public License v3.0](https://www.gnu.org/licenses/lgpl-3.0.html).
Qt's source code is available from <https://download.qt.io/official_releases/qt/>.
Because Mouse Plus's complete source code and build script are public, you can rebuild the exe with a modified version of Qt.

## Python (PSF License Agreement)

The exe contains the Python runtime and parts of its standard library, used under the
[PSF License Agreement](https://docs.python.org/3.12/license.html).

Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023 Python Software Foundation; All Rights Reserved.

## PyInstaller bootloader

The exe starts through PyInstaller's bootloader, licensed under the GNU General Public License v2.0 or later with this exception:

> In addition to the permissions in the GNU General Public License, the authors give you unlimited permission to link or embed compiled bootloader and related files into combinations with other programs, and to distribute those combinations without any restriction coming from the use of those files. (The General Public License restrictions do apply in other respects; for example, they cover modification of the files, and distribution when not linked into a combined executable.)

## BSD-licensed components

These licenses require their notices to be reproduced when the software is distributed in binary form.

### darkdetect

```text
Copyright (c) 2019, Alberto Sottile
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of "darkdetect" nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL "Alberto Sottile" BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### PyQt6-sip

```text
Copyright (c) 2025 Phil Thompson <phil@riverbankcomputing.com>

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### pywin32

The `win32` modules are under the license below. The COM modules (`win32com`, `pythoncom`) use the same terms,
Copyright (c) 1996-2008, Greg Stein and Mark Hammond.

```text
Unless stated in the specific source file, this work is
Copyright (c) 1994-2008, Mark Hammond
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in
the documentation and/or other materials provided with the distribution.

Neither name of Mark Hammond nor the name of contributors may be used
to endorse or promote products derived from this software without
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS ``AS
IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```
