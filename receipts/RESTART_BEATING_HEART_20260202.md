  [Restored Feb 2, 2026 at 4:55:12 PM]
Last login: Mon Feb  2 16:55:04 on console
You have new mail.

The default interactive shell is now zsh.
To update your account to use zsh, please run `chsh -s /bin/zsh`.
For more details, please visit https://support.apple.com/kb/HT208050.
www:2ndOpinionMD-MVP 2ndopinionmd$ docker-compose up --build
WARN[0000] /Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
unable to get image '2ndopinionmd-mvp-nginx': Cannot connect to the Docker daemon at unix:///Users/2ndopinionmd/.docker/run/docker.sock. Is the docker daemon running?
www:2ndOpinionMD-MVP 2ndopinionmd$ cd 2ndOpinionMD-MVP && rm -rf .BeatingHeart && ./SETUP_BEATING_HEART.sh
-bash: cd: 2ndOpinionMD-MVP: No such file or directory
www:2ndOpinionMD-MVP 2ndopinionmd$ rm -rf .BeatingHeart && ./SETUP_BEATING_HEART.sh
========================================
.BeatingHeart venv setup (2OPMD)
========================================
Using: python3.12 (Python 3.12.12)
Creating .BeatingHeart venv...
Upgrading pip...
Installing server requirements (uvicorn, fastapi, etc.)...
Collecting accelerate==0.34.2 (from -r server/requirements.txt (line 1))
  Using cached accelerate-0.34.2-py3-none-any.whl.metadata (19 kB)
Collecting aiohappyeyeballs==2.6.1 (from -r server/requirements.txt (line 2))
  Using cached aiohappyeyeballs-2.6.1-py3-none-any.whl.metadata (5.9 kB)
Collecting aiohttp==3.12.14 (from -r server/requirements.txt (line 3))
  Using cached aiohttp-3.12.14-cp312-cp312-macosx_11_0_arm64.whl.metadata (7.6 kB)
Collecting aiosignal==1.4.0 (from -r server/requirements.txt (line 4))
  Using cached aiosignal-1.4.0-py3-none-any.whl.metadata (3.7 kB)
Collecting aiosmtplib==2.0.2 (from -r server/requirements.txt (line 5))
  Using cached aiosmtplib-2.0.2-py3-none-any.whl.metadata (4.0 kB)
Collecting alembic==1.13.1 (from -r server/requirements.txt (line 6))
  Using cached alembic-1.13.1-py3-none-any.whl.metadata (7.4 kB)
Collecting annotated-types==0.7.0 (from -r server/requirements.txt (line 7))
  Using cached annotated_types-0.7.0-py3-none-any.whl.metadata (15 kB)
Collecting anthropic==0.72.1 (from -r server/requirements.txt (line 8))
  Using cached anthropic-0.72.1-py3-none-any.whl.metadata (28 kB)
Collecting anyio==4.9.0 (from -r server/requirements.txt (line 9))
  Using cached anyio-4.9.0-py3-none-any.whl.metadata (4.7 kB)
Collecting asyncpg==0.29.0 (from -r server/requirements.txt (line 10))
  Using cached asyncpg-0.29.0-cp312-cp312-macosx_11_0_arm64.whl.metadata (4.4 kB)
Collecting attrs==25.3.0 (from -r server/requirements.txt (line 11))
  Using cached attrs-25.3.0-py3-none-any.whl.metadata (10 kB)
Collecting bcrypt==4.1.2 (from -r server/requirements.txt (line 12))
  Using cached bcrypt-4.1.2-cp39-abi3-macosx_10_12_universal2.whl.metadata (9.5 kB)
Collecting beautifulsoup4==4.14.2 (from -r server/requirements.txt (line 13))
  Using cached beautifulsoup4-4.14.2-py3-none-any.whl.metadata (3.8 kB)
Collecting biothings_client==0.4.1 (from -r server/requirements.txt (line 14))
  Using cached biothings_client-0.4.1-py3-none-any.whl.metadata (10 kB)
Collecting blinker==1.9.0 (from -r server/requirements.txt (line 15))
  Using cached blinker-1.9.0-py3-none-any.whl.metadata (1.6 kB)
Collecting certifi==2025.7.14 (from -r server/requirements.txt (line 16))
  Using cached certifi-2025.7.14-py3-none-any.whl.metadata (2.4 kB)
Collecting cffi==1.17.1 (from -r server/requirements.txt (line 17))
  Using cached cffi-1.17.1-cp312-cp312-macosx_11_0_arm64.whl.metadata (1.5 kB)
Collecting chardet==5.2.0 (from -r server/requirements.txt (line 18))
  Using cached chardet-5.2.0-py3-none-any.whl.metadata (3.4 kB)
Collecting charset-normalizer==3.4.2 (from -r server/requirements.txt (line 19))
  Using cached charset_normalizer-3.4.2-cp312-cp312-macosx_10_13_universal2.whl.metadata (35 kB)
Collecting click==8.2.1 (from -r server/requirements.txt (line 20))
  Using cached click-8.2.1-py3-none-any.whl.metadata (2.5 kB)
Collecting cryptography==42.0.5 (from -r server/requirements.txt (line 21))
  Using cached cryptography-42.0.5-cp39-abi3-macosx_10_12_universal2.whl.metadata (5.3 kB)
Collecting datasets==2.20.0 (from -r server/requirements.txt (line 22))
  Using cached datasets-2.20.0-py3-none-any.whl.metadata (19 kB)
Collecting dill==0.3.8 (from -r server/requirements.txt (line 23))
  Using cached dill-0.3.8-py3-none-any.whl.metadata (10 kB)
Collecting distro==1.9.0 (from -r server/requirements.txt (line 24))
  Using cached distro-1.9.0-py3-none-any.whl.metadata (6.8 kB)
Collecting dnspython==2.7.0 (from -r server/requirements.txt (line 25))
  Using cached dnspython-2.7.0-py3-none-any.whl.metadata (5.8 kB)
Collecting docstring_parser==0.17.0 (from -r server/requirements.txt (line 26))
  Using cached docstring_parser-0.17.0-py3-none-any.whl.metadata (3.5 kB)
Collecting ecdsa==0.19.1 (from -r server/requirements.txt (line 27))
  Using cached ecdsa-0.19.1-py2.py3-none-any.whl.metadata (29 kB)
Collecting email_validator==2.2.0 (from -r server/requirements.txt (line 28))
  Using cached email_validator-2.2.0-py3-none-any.whl.metadata (25 kB)
Collecting et_xmlfile==2.0.0 (from -r server/requirements.txt (line 29))
  Using cached et_xmlfile-2.0.0-py3-none-any.whl.metadata (2.7 kB)
Collecting evaluate==0.4.2 (from -r server/requirements.txt (line 30))
  Using cached evaluate-0.4.2-py3-none-any.whl.metadata (9.3 kB)
Collecting fastapi==0.109.2 (from -r server/requirements.txt (line 31))
  Using cached fastapi-0.109.2-py3-none-any.whl.metadata (25 kB)
Collecting fastapi-mail==1.4.1 (from -r server/requirements.txt (line 32))
  Using cached fastapi_mail-1.4.1-py3-none-any.whl.metadata (4.7 kB)
Collecting filelock==3.19.1 (from -r server/requirements.txt (line 33))
  Using cached filelock-3.19.1-py3-none-any.whl.metadata (2.1 kB)
Collecting frozenlist==1.7.0 (from -r server/requirements.txt (line 34))
  Using cached frozenlist-1.7.0-cp312-cp312-macosx_11_0_arm64.whl.metadata (18 kB)
Collecting fsspec==2024.5.0 (from -r server/requirements.txt (line 35))
  Using cached fsspec-2024.5.0-py3-none-any.whl.metadata (11 kB)
Collecting gitdb==4.0.12 (from -r server/requirements.txt (line 36))
  Using cached gitdb-4.0.12-py3-none-any.whl.metadata (1.2 kB)
Collecting GitPython==3.1.45 (from -r server/requirements.txt (line 37))
  Using cached gitpython-3.1.45-py3-none-any.whl.metadata (13 kB)
Collecting greenlet==3.2.3 (from -r server/requirements.txt (line 38))
  Using cached greenlet-3.2.3-cp312-cp312-macosx_11_0_universal2.whl.metadata (4.1 kB)
Collecting h11==0.16.0 (from -r server/requirements.txt (line 39))
  Using cached h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
Collecting hf-xet==1.1.10 (from -r server/requirements.txt (line 40))
  Using cached hf_xet-1.1.10-cp37-abi3-macosx_11_0_arm64.whl.metadata (4.7 kB)
Collecting httpcore==1.0.9 (from -r server/requirements.txt (line 41))
  Using cached httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
Collecting httpx==0.27.0 (from -r server/requirements.txt (line 42))
  Using cached httpx-0.27.0-py3-none-any.whl.metadata (7.2 kB)
Collecting huggingface-hub==0.34.4 (from -r server/requirements.txt (line 43))
  Using cached huggingface_hub-0.34.4-py3-none-any.whl.metadata (14 kB)
Collecting idna==3.10 (from -r server/requirements.txt (line 44))
  Using cached idna-3.10-py3-none-any.whl.metadata (10 kB)
Collecting Jinja2==3.1.6 (from -r server/requirements.txt (line 45))
  Using cached jinja2-3.1.6-py3-none-any.whl.metadata (2.9 kB)
Collecting jiter==0.10.0 (from -r server/requirements.txt (line 46))
  Using cached jiter-0.10.0-cp312-cp312-macosx_11_0_arm64.whl.metadata (5.2 kB)
Collecting joblib==1.5.1 (from -r server/requirements.txt (line 47))
  Using cached joblib-1.5.1-py3-none-any.whl.metadata (5.6 kB)
Collecting lxml==6.0.2 (from -r server/requirements.txt (line 48))
  Using cached lxml-6.0.2-cp312-cp312-macosx_10_13_universal2.whl.metadata (3.6 kB)
Collecting Mako==1.3.10 (from -r server/requirements.txt (line 49))
  Using cached mako-1.3.10-py3-none-any.whl.metadata (2.9 kB)
Collecting markdown-it-py==4.0.0 (from -r server/requirements.txt (line 50))
  Using cached markdown_it_py-4.0.0-py3-none-any.whl.metadata (7.3 kB)
Collecting MarkupSafe==3.0.2 (from -r server/requirements.txt (line 51))
  Using cached MarkupSafe-3.0.2-cp312-cp312-macosx_11_0_arm64.whl.metadata (4.0 kB)
Collecting mdurl==0.1.2 (from -r server/requirements.txt (line 52))
  Using cached mdurl-0.1.2-py3-none-any.whl.metadata (1.6 kB)
Collecting motor==3.3.2 (from -r server/requirements.txt (line 53))
  Using cached motor-3.3.2-py3-none-any.whl.metadata (20 kB)
Collecting mpmath==1.3.0 (from -r server/requirements.txt (line 54))
  Using cached mpmath-1.3.0-py3-none-any.whl.metadata (8.6 kB)
Collecting multidict==6.6.3 (from -r server/requirements.txt (line 55))
  Using cached multidict-6.6.3-cp312-cp312-macosx_11_0_arm64.whl.metadata (5.3 kB)
Collecting multiprocess==0.70.16 (from -r server/requirements.txt (line 56))
  Using cached multiprocess-0.70.16-py312-none-any.whl.metadata (7.2 kB)
Collecting mygene==3.2.2 (from -r server/requirements.txt (line 57))
  Using cached mygene-3.2.2-py2.py3-none-any.whl.metadata (10 kB)
Collecting networkx==3.5 (from -r server/requirements.txt (line 58))
  Using cached networkx-3.5-py3-none-any.whl.metadata (6.3 kB)
Collecting numpy<2.5,>=1.26.3 (from -r server/requirements.txt (line 59))
  Using cached numpy-2.4.2-cp312-cp312-macosx_14_0_arm64.whl.metadata (6.6 kB)
Collecting openai==1.109.1 (from -r server/requirements.txt (line 60))
  Using cached openai-1.109.1-py3-none-any.whl.metadata (29 kB)
Collecting openpyxl==3.1.5 (from -r server/requirements.txt (line 61))
  Using cached openpyxl-3.1.5-py2.py3-none-any.whl.metadata (2.5 kB)
Collecting packaging==25.0 (from -r server/requirements.txt (line 62))
  Using cached packaging-25.0-py3-none-any.whl.metadata (3.3 kB)
Collecting pandas==2.3.3 (from -r server/requirements.txt (line 63))
  Using cached pandas-2.3.3-cp312-cp312-macosx_11_0_arm64.whl.metadata (91 kB)
Collecting passlib==1.7.4 (from -r server/requirements.txt (line 64))
  Using cached passlib-1.7.4-py2.py3-none-any.whl.metadata (1.7 kB)
Collecting pdfminer.six==20250506 (from -r server/requirements.txt (line 65))
  Using cached pdfminer_six-20250506-py3-none-any.whl.metadata (4.2 kB)
Collecting pgvector==0.2.4 (from -r server/requirements.txt (line 66))
  Using cached pgvector-0.2.4-py2.py3-none-any.whl.metadata (9.8 kB)
Collecting pillow==11.3.0 (from -r server/requirements.txt (line 67))
  Using cached pillow-11.3.0-cp312-cp312-macosx_11_0_arm64.whl.metadata (9.0 kB)
Collecting platformdirs==4.4.0 (from -r server/requirements.txt (line 68))
  Using cached platformdirs-4.4.0-py3-none-any.whl.metadata (12 kB)
Collecting propcache==0.3.2 (from -r server/requirements.txt (line 69))
  Using cached propcache-0.3.2-cp312-cp312-macosx_11_0_arm64.whl.metadata (12 kB)
Collecting protobuf==6.32.1 (from -r server/requirements.txt (line 70))
  Using cached protobuf-6.32.1-cp39-abi3-macosx_10_9_universal2.whl.metadata (593 bytes)
Collecting psutil==7.0.0 (from -r server/requirements.txt (line 71))
  Using cached psutil-7.0.0-cp36-abi3-macosx_11_0_arm64.whl.metadata (22 kB)
Collecting psycopg<3.4,>=3.2.10 (from -r server/requirements.txt (line 72))
  Using cached psycopg-3.3.2-py3-none-any.whl.metadata (4.3 kB)
Collecting psycopg-binary<3.4,>=3.2.10 (from -r server/requirements.txt (line 73))
  Using cached psycopg_binary-3.3.2-cp312-cp312-macosx_11_0_arm64.whl.metadata (2.7 kB)
Collecting psycopg2==2.9.10 (from -r server/requirements.txt (line 74))
  Using cached psycopg2-2.9.10-cp312-cp312-macosx_15_0_arm64.whl
Collecting psycopg2-binary==2.9.9 (from -r server/requirements.txt (line 75))
  Using cached psycopg2_binary-2.9.9-cp312-cp312-macosx_11_0_arm64.whl.metadata (4.4 kB)
Collecting pyarrow==21.0.0 (from -r server/requirements.txt (line 76))
  Using cached pyarrow-21.0.0-cp312-cp312-macosx_12_0_arm64.whl.metadata (3.3 kB)
Collecting pyarrow-hotfix==0.7 (from -r server/requirements.txt (line 77))
  Using cached pyarrow_hotfix-0.7-py3-none-any.whl.metadata (3.6 kB)
Collecting pyasn1==0.6.1 (from -r server/requirements.txt (line 78))
  Using cached pyasn1-0.6.1-py3-none-any.whl.metadata (8.4 kB)
Collecting pycparser==2.22 (from -r server/requirements.txt (line 79))
  Using cached pycparser-2.22-py3-none-any.whl.metadata (943 bytes)
Collecting pydantic==2.5.3 (from -r server/requirements.txt (line 80))
  Using cached pydantic-2.5.3-py3-none-any.whl.metadata (65 kB)
Collecting pydantic-settings==2.2.1 (from -r server/requirements.txt (line 81))
  Using cached pydantic_settings-2.2.1-py3-none-any.whl.metadata (3.1 kB)
Collecting pydantic_core==2.14.6 (from -r server/requirements.txt (line 82))
  Using cached pydantic_core-2.14.6-cp312-cp312-macosx_11_0_arm64.whl.metadata (6.5 kB)
Collecting Pygments==2.19.2 (from -r server/requirements.txt (line 83))
  Using cached pygments-2.19.2-py3-none-any.whl.metadata (2.5 kB)
Collecting pymongo==4.6.1 (from -r server/requirements.txt (line 84))
  Using cached pymongo-4.6.1-cp312-cp312-macosx_10_9_universal2.whl.metadata (22 kB)
Collecting pypdf==6.1.1 (from -r server/requirements.txt (line 85))
  Using cached pypdf-6.1.1-py3-none-any.whl.metadata (7.1 kB)
Collecting python-calamine==0.5.3 (from -r server/requirements.txt (line 86))
  Using cached python_calamine-0.5.3-cp312-cp312-macosx_11_0_arm64.whl.metadata (3.1 kB)
Collecting python-dateutil==2.9.0.post0 (from -r server/requirements.txt (line 87))
  Using cached python_dateutil-2.9.0.post0-py2.py3-none-any.whl.metadata (8.4 kB)
Collecting python-dotenv==1.0.0 (from -r server/requirements.txt (line 88))
  Using cached python_dotenv-1.0.0-py3-none-any.whl.metadata (21 kB)
Collecting python-jose==3.3.0 (from -r server/requirements.txt (line 89))
  Using cached python_jose-3.3.0-py2.py3-none-any.whl.metadata (5.4 kB)
Collecting python-multipart==0.0.6 (from -r server/requirements.txt (line 90))
  Using cached python_multipart-0.0.6-py3-none-any.whl.metadata (2.5 kB)
Collecting pytz==2025.2 (from -r server/requirements.txt (line 91))
  Using cached pytz-2025.2-py2.py3-none-any.whl.metadata (22 kB)
Collecting PyYAML==6.0.2 (from -r server/requirements.txt (line 92))
  Using cached PyYAML-6.0.2-cp312-cp312-macosx_11_0_arm64.whl.metadata (2.1 kB)
Collecting regex==2025.9.1 (from -r server/requirements.txt (line 93))
  Using cached regex-2025.9.1-cp312-cp312-macosx_11_0_arm64.whl.metadata (40 kB)
Collecting reportlab==4.2.2 (from -r server/requirements.txt (line 94))
  Using cached reportlab-4.2.2-py3-none-any.whl.metadata (1.4 kB)
Collecting requests==2.32.3 (from -r server/requirements.txt (line 95))
  Using cached requests-2.32.3-py3-none-any.whl.metadata (4.6 kB)
Collecting rich==14.1.0 (from -r server/requirements.txt (line 96))
  Using cached rich-14.1.0-py3-none-any.whl.metadata (18 kB)
Collecting rsa==4.9.1 (from -r server/requirements.txt (line 97))
  Using cached rsa-4.9.1-py3-none-any.whl.metadata (5.6 kB)
Collecting safetensors==0.6.2 (from -r server/requirements.txt (line 98))
  Using cached safetensors-0.6.2-cp38-abi3-macosx_11_0_arm64.whl.metadata (4.1 kB)
Collecting scikit-learn<2,>=1.3.0 (from -r server/requirements.txt (line 99))
  Using cached scikit_learn-1.8.0-cp312-cp312-macosx_12_0_arm64.whl.metadata (11 kB)
Collecting scipy==1.16.1 (from -r server/requirements.txt (line 100))
  Using cached scipy-1.16.1-cp312-cp312-macosx_14_0_arm64.whl.metadata (61 kB)
Collecting sentry-sdk==2.37.1 (from -r server/requirements.txt (line 101))
  Using cached sentry_sdk-2.37.1-py2.py3-none-any.whl.metadata (10 kB)
Collecting setuptools==80.9.0 (from -r server/requirements.txt (line 102))
  Using cached setuptools-80.9.0-py3-none-any.whl.metadata (6.6 kB)
Collecting six==1.17.0 (from -r server/requirements.txt (line 103))
  Using cached six-1.17.0-py2.py3-none-any.whl.metadata (1.7 kB)
Collecting smmap==5.0.2 (from -r server/requirements.txt (line 104))
  Using cached smmap-5.0.2-py3-none-any.whl.metadata (4.3 kB)
Collecting sniffio==1.3.1 (from -r server/requirements.txt (line 105))
  Using cached sniffio-1.3.1-py3-none-any.whl.metadata (3.9 kB)
Collecting soupsieve==2.8 (from -r server/requirements.txt (line 106))
  Using cached soupsieve-2.8-py3-none-any.whl.metadata (4.6 kB)
Collecting SQLAlchemy==2.0.25 (from -r server/requirements.txt (line 107))
  Using cached SQLAlchemy-2.0.25-cp312-cp312-macosx_11_0_arm64.whl.metadata (9.6 kB)
Collecting sse-starlette==3.0.3 (from -r server/requirements.txt (line 108))
  Using cached sse_starlette-3.0.3-py3-none-any.whl.metadata (12 kB)
Collecting starlette==0.36.3 (from -r server/requirements.txt (line 109))
  Using cached starlette-0.36.3-py3-none-any.whl.metadata (5.9 kB)
Collecting sympy==1.14.0 (from -r server/requirements.txt (line 110))
  Using cached sympy-1.14.0-py3-none-any.whl.metadata (12 kB)
Collecting threadpoolctl==3.6.0 (from -r server/requirements.txt (line 111))
  Using cached threadpoolctl-3.6.0-py3-none-any.whl.metadata (13 kB)
Collecting tokenizers==0.19.1 (from -r server/requirements.txt (line 112))
  Using cached tokenizers-0.19.1-cp312-cp312-macosx_11_0_arm64.whl.metadata (6.7 kB)
Collecting torch==2.8.0 (from -r server/requirements.txt (line 113))
  Using cached torch-2.8.0-cp312-none-macosx_11_0_arm64.whl.metadata (30 kB)
Collecting tqdm==4.67.1 (from -r server/requirements.txt (line 114))
  Using cached tqdm-4.67.1-py3-none-any.whl.metadata (57 kB)
Collecting transformers==4.44.2 (from -r server/requirements.txt (line 115))
  Using cached transformers-4.44.2-py3-none-any.whl.metadata (43 kB)
Collecting typing_extensions==4.14.1 (from -r server/requirements.txt (line 116))
  Using cached typing_extensions-4.14.1-py3-none-any.whl.metadata (3.0 kB)
Collecting tzdata==2025.2 (from -r server/requirements.txt (line 117))
  Using cached tzdata-2025.2-py2.py3-none-any.whl.metadata (1.4 kB)
Collecting urllib3==2.5.0 (from -r server/requirements.txt (line 118))
  Using cached urllib3-2.5.0-py3-none-any.whl.metadata (6.5 kB)
Collecting uvicorn==0.27.1 (from -r server/requirements.txt (line 119))
  Using cached uvicorn-0.27.1-py3-none-any.whl.metadata (6.3 kB)
Collecting valyu==2.2.2 (from -r server/requirements.txt (line 120))
  Using cached valyu-2.2.2-py3-none-any.whl.metadata (16 kB)
Collecting wandb==0.21.4 (from -r server/requirements.txt (line 121))
  Using cached wandb-0.21.4-py3-none-macosx_12_0_arm64.whl.metadata (10 kB)
Collecting watch==0.2.7 (from -r server/requirements.txt (line 122))
  Using cached watch-0.2.7-py3-none-any.whl
Collecting wheel==0.45.1 (from -r server/requirements.txt (line 123))
  Using cached wheel-0.45.1-py3-none-any.whl.metadata (2.3 kB)
Collecting xxhash==3.5.0 (from -r server/requirements.txt (line 124))
  Using cached xxhash-3.5.0-cp312-cp312-macosx_11_0_arm64.whl.metadata (12 kB)
Collecting yarl==1.20.1 (from -r server/requirements.txt (line 125))
  Using cached yarl-1.20.1-cp312-cp312-macosx_11_0_arm64.whl.metadata (73 kB)
Using cached accelerate-0.34.2-py3-none-any.whl (324 kB)
Using cached aiohappyeyeballs-2.6.1-py3-none-any.whl (15 kB)
Using cached aiohttp-3.12.14-cp312-cp312-macosx_11_0_arm64.whl (468 kB)
Using cached multidict-6.6.3-cp312-cp312-macosx_11_0_arm64.whl (43 kB)
Using cached yarl-1.20.1-cp312-cp312-macosx_11_0_arm64.whl (89 kB)
Using cached aiosignal-1.4.0-py3-none-any.whl (7.5 kB)
Using cached aiosmtplib-2.0.2-py3-none-any.whl (27 kB)
Using cached alembic-1.13.1-py3-none-any.whl (233 kB)
Using cached annotated_types-0.7.0-py3-none-any.whl (13 kB)
Using cached anthropic-0.72.1-py3-none-any.whl (357 kB)
Using cached anyio-4.9.0-py3-none-any.whl (100 kB)
Using cached distro-1.9.0-py3-none-any.whl (20 kB)
Using cached docstring_parser-0.17.0-py3-none-any.whl (36 kB)
Using cached httpx-0.27.0-py3-none-any.whl (75 kB)
Using cached httpcore-1.0.9-py3-none-any.whl (78 kB)
Using cached jiter-0.10.0-cp312-cp312-macosx_11_0_arm64.whl (320 kB)
Using cached pydantic-2.5.3-py3-none-any.whl (381 kB)
Using cached typing_extensions-4.14.1-py3-none-any.whl (43 kB)
Using cached asyncpg-0.29.0-cp312-cp312-macosx_11_0_arm64.whl (618 kB)
Using cached attrs-25.3.0-py3-none-any.whl (63 kB)
Using cached bcrypt-4.1.2-cp39-abi3-macosx_10_12_universal2.whl (528 kB)
Using cached beautifulsoup4-4.14.2-py3-none-any.whl (106 kB)
Using cached biothings_client-0.4.1-py3-none-any.whl (46 kB)
Using cached blinker-1.9.0-py3-none-any.whl (8.5 kB)
Using cached certifi-2025.7.14-py3-none-any.whl (162 kB)
Using cached cffi-1.17.1-cp312-cp312-macosx_11_0_arm64.whl (178 kB)
Using cached chardet-5.2.0-py3-none-any.whl (199 kB)
Using cached charset_normalizer-3.4.2-cp312-cp312-macosx_10_13_universal2.whl (199 kB)
Using cached click-8.2.1-py3-none-any.whl (102 kB)
Using cached cryptography-42.0.5-cp39-abi3-macosx_10_12_universal2.whl (5.9 MB)
Using cached datasets-2.20.0-py3-none-any.whl (547 kB)
Using cached dill-0.3.8-py3-none-any.whl (116 kB)
Using cached fsspec-2024.5.0-py3-none-any.whl (316 kB)
Using cached dnspython-2.7.0-py3-none-any.whl (313 kB)
Using cached ecdsa-0.19.1-py2.py3-none-any.whl (150 kB)
Using cached email_validator-2.2.0-py3-none-any.whl (33 kB)
Using cached et_xmlfile-2.0.0-py3-none-any.whl (18 kB)
Using cached evaluate-0.4.2-py3-none-any.whl (84 kB)
Using cached fastapi-0.109.2-py3-none-any.whl (92 kB)
Using cached starlette-0.36.3-py3-none-any.whl (71 kB)
Using cached fastapi_mail-1.4.1-py3-none-any.whl (14 kB)
Using cached jinja2-3.1.6-py3-none-any.whl (134 kB)
Using cached pydantic_settings-2.2.1-py3-none-any.whl (13 kB)
Using cached filelock-3.19.1-py3-none-any.whl (15 kB)
Using cached frozenlist-1.7.0-cp312-cp312-macosx_11_0_arm64.whl (46 kB)
Using cached gitdb-4.0.12-py3-none-any.whl (62 kB)
Using cached smmap-5.0.2-py3-none-any.whl (24 kB)
Using cached gitpython-3.1.45-py3-none-any.whl (208 kB)
Using cached greenlet-3.2.3-cp312-cp312-macosx_11_0_universal2.whl (271 kB)
Using cached h11-0.16.0-py3-none-any.whl (37 kB)
Using cached hf_xet-1.1.10-cp37-abi3-macosx_11_0_arm64.whl (2.6 MB)
Using cached huggingface_hub-0.34.4-py3-none-any.whl (561 kB)
Using cached idna-3.10-py3-none-any.whl (70 kB)
Using cached joblib-1.5.1-py3-none-any.whl (307 kB)
Using cached lxml-6.0.2-cp312-cp312-macosx_10_13_universal2.whl (8.7 MB)
Using cached mako-1.3.10-py3-none-any.whl (78 kB)
Using cached markdown_it_py-4.0.0-py3-none-any.whl (87 kB)
Using cached mdurl-0.1.2-py3-none-any.whl (10.0 kB)
Using cached MarkupSafe-3.0.2-cp312-cp312-macosx_11_0_arm64.whl (12 kB)
Using cached motor-3.3.2-py3-none-any.whl (70 kB)
Using cached pymongo-4.6.1-cp312-cp312-macosx_10_9_universal2.whl (533 kB)
Using cached mpmath-1.3.0-py3-none-any.whl (536 kB)
Using cached multiprocess-0.70.16-py312-none-any.whl (146 kB)
Using cached mygene-3.2.2-py2.py3-none-any.whl (5.4 kB)
Using cached networkx-3.5-py3-none-any.whl (2.0 MB)
Using cached openai-1.109.1-py3-none-any.whl (948 kB)
Using cached openpyxl-3.1.5-py2.py3-none-any.whl (250 kB)
Using cached packaging-25.0-py3-none-any.whl (66 kB)
Using cached pandas-2.3.3-cp312-cp312-macosx_11_0_arm64.whl (10.7 MB)
Using cached passlib-1.7.4-py2.py3-none-any.whl (525 kB)
Using cached pdfminer_six-20250506-py3-none-any.whl (5.6 MB)
Using cached pgvector-0.2.4-py2.py3-none-any.whl (9.6 kB)
Using cached pillow-11.3.0-cp312-cp312-macosx_11_0_arm64.whl (4.7 MB)
Using cached platformdirs-4.4.0-py3-none-any.whl (18 kB)
Using cached propcache-0.3.2-cp312-cp312-macosx_11_0_arm64.whl (43 kB)
Using cached protobuf-6.32.1-cp39-abi3-macosx_10_9_universal2.whl (426 kB)
Using cached psutil-7.0.0-cp36-abi3-macosx_11_0_arm64.whl (239 kB)
Using cached psycopg2_binary-2.9.9-cp312-cp312-macosx_11_0_arm64.whl (2.6 MB)
Using cached pyarrow-21.0.0-cp312-cp312-macosx_12_0_arm64.whl (31.2 MB)
Using cached pyarrow_hotfix-0.7-py3-none-any.whl (7.9 kB)
Using cached pyasn1-0.6.1-py3-none-any.whl (83 kB)
Using cached pycparser-2.22-py3-none-any.whl (117 kB)
Using cached pydantic_core-2.14.6-cp312-cp312-macosx_11_0_arm64.whl (1.7 MB)
Using cached pygments-2.19.2-py3-none-any.whl (1.2 MB)
Using cached pypdf-6.1.1-py3-none-any.whl (323 kB)
Using cached python_calamine-0.5.3-cp312-cp312-macosx_11_0_arm64.whl (814 kB)
Using cached python_dateutil-2.9.0.post0-py2.py3-none-any.whl (229 kB)
Using cached python_dotenv-1.0.0-py3-none-any.whl (19 kB)
Using cached python_jose-3.3.0-py2.py3-none-any.whl (33 kB)
Using cached python_multipart-0.0.6-py3-none-any.whl (45 kB)
Using cached pytz-2025.2-py2.py3-none-any.whl (509 kB)
Using cached PyYAML-6.0.2-cp312-cp312-macosx_11_0_arm64.whl (173 kB)
Using cached regex-2025.9.1-cp312-cp312-macosx_11_0_arm64.whl (287 kB)
Using cached reportlab-4.2.2-py3-none-any.whl (1.9 MB)
Using cached requests-2.32.3-py3-none-any.whl (64 kB)
Using cached urllib3-2.5.0-py3-none-any.whl (129 kB)
Using cached rich-14.1.0-py3-none-any.whl (243 kB)
Using cached rsa-4.9.1-py3-none-any.whl (34 kB)
Using cached safetensors-0.6.2-cp38-abi3-macosx_11_0_arm64.whl (432 kB)
Using cached scipy-1.16.1-cp312-cp312-macosx_14_0_arm64.whl (20.9 MB)
Using cached sentry_sdk-2.37.1-py2.py3-none-any.whl (368 kB)
Using cached setuptools-80.9.0-py3-none-any.whl (1.2 MB)
Using cached six-1.17.0-py2.py3-none-any.whl (11 kB)
Using cached sniffio-1.3.1-py3-none-any.whl (10 kB)
Using cached soupsieve-2.8-py3-none-any.whl (36 kB)
Using cached SQLAlchemy-2.0.25-cp312-cp312-macosx_11_0_arm64.whl (2.1 MB)
Using cached sse_starlette-3.0.3-py3-none-any.whl (11 kB)
Using cached sympy-1.14.0-py3-none-any.whl (6.3 MB)
Using cached threadpoolctl-3.6.0-py3-none-any.whl (18 kB)
Using cached tokenizers-0.19.1-cp312-cp312-macosx_11_0_arm64.whl (2.4 MB)
Using cached torch-2.8.0-cp312-none-macosx_11_0_arm64.whl (73.6 MB)
Using cached tqdm-4.67.1-py3-none-any.whl (78 kB)
Using cached transformers-4.44.2-py3-none-any.whl (9.5 MB)
Using cached tzdata-2025.2-py2.py3-none-any.whl (347 kB)
Using cached uvicorn-0.27.1-py3-none-any.whl (60 kB)
Using cached valyu-2.2.2-py3-none-any.whl (22 kB)
Using cached wandb-0.21.4-py3-none-macosx_12_0_arm64.whl (18.3 MB)
Using cached wheel-0.45.1-py3-none-any.whl (72 kB)
Using cached xxhash-3.5.0-cp312-cp312-macosx_11_0_arm64.whl (30 kB)
Using cached numpy-2.4.2-cp312-cp312-macosx_14_0_arm64.whl (5.2 MB)
Using cached psycopg-3.3.2-py3-none-any.whl (212 kB)
Using cached psycopg_binary-3.3.2-cp312-cp312-macosx_11_0_arm64.whl (4.7 MB)
Using cached scikit_learn-1.8.0-cp312-cp312-macosx_12_0_arm64.whl (8.1 MB)
Installing collected packages: watch, pytz, passlib, mpmath, xxhash, wheel, urllib3, tzdata, typing_extensions, tqdm, threadpoolctl, sympy, soupsieve, sniffio, smmap, six, setuptools, safetensors, regex, PyYAML, python-multipart, python-dotenv, python-calamine, pypdf, Pygments, pycparser, pyasn1, pyarrow-hotfix, pyarrow, psycopg2-binary, psycopg2, psycopg-binary, psutil, protobuf, propcache, platformdirs, pillow, packaging, numpy, networkx, multidict, mdurl, MarkupSafe, lxml, joblib, jiter, idna, hf-xet, h11, greenlet, fsspec, frozenlist, filelock, et_xmlfile, docstring_parser, dnspython, distro, dill, click, charset-normalizer, chardet, certifi, blinker, bcrypt, attrs, asyncpg, annotated-types, aiosmtplib, aiohappyeyeballs, yarl, uvicorn, SQLAlchemy, sentry-sdk, scipy, rsa, requests, reportlab, python-dateutil, pymongo, pydantic_core, psycopg, pgvector, openpyxl, multiprocess, markdown-it-py, Mako, Jinja2, httpcore, gitdb, email_validator, ecdsa, cffi, beautifulsoup4, anyio, aiosignal, torch, starlette, sse-starlette, scikit-learn, rich, python-jose, pydantic, pandas, motor, huggingface-hub, httpx, GitPython, cryptography, alembic, aiohttp, wandb, tokenizers, pydantic-settings, pdfminer.six, openai, fastapi, biothings_client, anthropic, accelerate, valyu, transformers, mygene, fastapi-mail, datasets, evaluate
Successfully installed GitPython-3.1.45 Jinja2-3.1.6 Mako-1.3.10 MarkupSafe-3.0.2 PyYAML-6.0.2 Pygments-2.19.2 SQLAlchemy-2.0.25 accelerate-0.34.2 aiohappyeyeballs-2.6.1 aiohttp-3.12.14 aiosignal-1.4.0 aiosmtplib-2.0.2 alembic-1.13.1 annotated-types-0.7.0 anthropic-0.72.1 anyio-4.9.0 asyncpg-0.29.0 attrs-25.3.0 bcrypt-4.1.2 beautifulsoup4-4.14.2 biothings_client-0.4.1 blinker-1.9.0 certifi-2025.7.14 cffi-1.17.1 chardet-5.2.0 charset-normalizer-3.4.2 click-8.2.1 cryptography-42.0.5 datasets-2.20.0 dill-0.3.8 distro-1.9.0 dnspython-2.7.0 docstring_parser-0.17.0 ecdsa-0.19.1 email_validator-2.2.0 et_xmlfile-2.0.0 evaluate-0.4.2 fastapi-0.109.2 fastapi-mail-1.4.1 filelock-3.19.1 frozenlist-1.7.0 fsspec-2024.5.0 gitdb-4.0.12 greenlet-3.2.3 h11-0.16.0 hf-xet-1.1.10 httpcore-1.0.9 httpx-0.27.0 huggingface-hub-0.34.4 idna-3.10 jiter-0.10.0 joblib-1.5.1 lxml-6.0.2 markdown-it-py-4.0.0 mdurl-0.1.2 motor-3.3.2 mpmath-1.3.0 multidict-6.6.3 multiprocess-0.70.16 mygene-3.2.2 networkx-3.5 numpy-2.4.2 openai-1.109.1 openpyxl-3.1.5 packaging-25.0 pandas-2.3.3 passlib-1.7.4 pdfminer.six-20250506 pgvector-0.2.4 pillow-11.3.0 platformdirs-4.4.0 propcache-0.3.2 protobuf-6.32.1 psutil-7.0.0 psycopg-3.3.2 psycopg-binary-3.3.2 psycopg2-2.9.10 psycopg2-binary-2.9.9 pyarrow-21.0.0 pyarrow-hotfix-0.7 pyasn1-0.6.1 pycparser-2.22 pydantic-2.5.3 pydantic-settings-2.2.1 pydantic_core-2.14.6 pymongo-4.6.1 pypdf-6.1.1 python-calamine-0.5.3 python-dateutil-2.9.0.post0 python-dotenv-1.0.0 python-jose-3.3.0 python-multipart-0.0.6 pytz-2025.2 regex-2025.9.1 reportlab-4.2.2 requests-2.32.3 rich-14.1.0 rsa-4.9.1 safetensors-0.6.2 scikit-learn-1.8.0 scipy-1.16.1 sentry-sdk-2.37.1 setuptools-80.9.0 six-1.17.0 smmap-5.0.2 sniffio-1.3.1 soupsieve-2.8 sse-starlette-3.0.3 starlette-0.36.3 sympy-1.14.0 threadpoolctl-3.6.0 tokenizers-0.19.1 torch-2.8.0 tqdm-4.67.1 transformers-4.44.2 typing_extensions-4.14.1 tzdata-2025.2 urllib3-2.5.0 uvicorn-0.27.1 valyu-2.2.2 wandb-0.21.4 watch-0.2.7 wheel-0.45.1 xxhash-3.5.0 yarl-1.20.1

✅ .BeatingHeart ready.

Activate and run server:
  source .BeatingHeart/bin/activate
  python server/scripts/run_postgres_app.py

Config: copy .env.example to .pulse or .env.
  SYNC_DATABASE_URL (postgresql://...) is used for rag_corpus and is the most important.
  DATABASE_URL can be the same URL; the app will use +asyncpg for the async server.
  (Optional: server/.pulse or server/.env for overrides; .pulse is loaded before .env)

www:2ndOpinionMD-MVP 2ndopinionmd$ ./RUN_POSTGRES_APP.sh
🚀 Starting FastAPI application on http://0.0.0.0:8000
📚 API documentation available at: http://0.0.0.0:8000/docs
Database connection will be initialized during FastAPI lifespan startup
2026-02-02 16:58:49,169 - root - INFO - Encrypted logging initialized. Log file: ./logs/server.log
Traceback (most recent call last):
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/server/scripts/run_postgres_app.py", line 41, in <module>
    main()
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/server/scripts/run_postgres_app.py", line 31, in main
    uvicorn.run(
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/uvicorn/main.py", line 587, in run
    server.run()
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/uvicorn/server.py", line 62, in run
    return asyncio.run(self.serve(sockets=sockets))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.12/3.12.12/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.12/3.12.12/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.12/3.12.12/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/base_events.py", line 691, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/uvicorn/server.py", line 69, in serve
    config.load()
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/uvicorn/config.py", line 458, in load
    self.loaded_app = import_from_string(self.app)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/uvicorn/importer.py", line 21, in import_from_string
    module = importlib.import_module(module_str)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.12/3.12.12/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 999, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/server/api/app_postgres.py", line 54, in <module>
    from server.vectordb.postgresql_query_engine import PostgreSQLMedicalQueryEngine
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/server/vectordb/postgresql_query_engine.py", line 11, in <module>
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/openai/_client.py", line 135, in __init__
    raise OpenAIError(
openai.OpenAIError: The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable
www:2ndOpinionMD-MVP 2ndopinionmd$ cat .env
cat: .env: No such file or directory
www:2ndOpinionMD-MVP 2ndopinionmd$ export OPENAI_API_KEY=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
www:2ndOpinionMD-MVP 2ndopinionmd$ ./RUN_POSTGRES_APP.sh
🚀 Starting FastAPI application on http://0.0.0.0:8000
📚 API documentation available at: http://0.0.0.0:8000/docs
Database connection will be initialized during FastAPI lifespan startup
2026-02-02 17:01:01,193 - root - INFO - Encrypted logging initialized. Log file: ./logs/server.log
2026-02-02 17:01:02,732 - server.api.kg - INFO - kg.py loaded. OPENAI_API_KEY set: yes
2026-02-02 17:01:02,732 - root - INFO - VALYU_API_KEY present: False tail=None
INFO:     Started server process [2482]
INFO:     Waiting for application startup.
ERROR:    Traceback (most recent call last):
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/starlette/routing.py", line 734, in lifespan
    async with self.lifespan_context(app) as maybe_state:
               ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.12/3.12.12/Frameworks/Python.framework/Versions/3.12/lib/python3.12/contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/server/api/app_postgres.py", line 110, in lifespan
    raise RuntimeError("No DATABASE_URL or SYNC_DATABASE_URL set in environment")
RuntimeError: No DATABASE_URL or SYNC_DATABASE_URL set in environment

ERROR:    Application startup failed. Exiting.
www:2ndOpinionMD-MVP 2ndopinionmd$ ./RUN_POSTGRES_APP.sh
🚀 Starting FastAPI application on http://0.0.0.0:8000
📚 API documentation available at: http://0.0.0.0:8000/docs
Database connection will be initialized during FastAPI lifespan startup
2026-02-02 17:04:18,522 - root - INFO - Encrypted logging initialized. Log file: ./logs/server.log
Traceback (most recent call last):
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/server/scripts/run_postgres_app.py", line 41, in <module>
    main()
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/server/scripts/run_postgres_app.py", line 31, in main
    uvicorn.run(
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/uvicorn/main.py", line 587, in run
    server.run()
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/uvicorn/server.py", line 62, in run
    return asyncio.run(self.serve(sockets=sockets))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.12/3.12.12/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/runners.py", line 195, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.12/3.12.12/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.12/3.12.12/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/base_events.py", line 691, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/uvicorn/server.py", line 69, in serve
    config.load()
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/uvicorn/config.py", line 458, in load
    self.loaded_app = import_from_string(self.app)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/uvicorn/importer.py", line 21, in import_from_string
    module = importlib.import_module(module_str)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.12/3.12.12/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 999, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/server/api/app_postgres.py", line 58, in <module>
    from server.api.journal import router as journal_router
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/server/api/journal.py", line 63, in <module>
    raise ValueError("OPENAI_API_KEY environment variable not set")
ValueError: OPENAI_API_KEY environment variable not set
www:2ndOpinionMD-MVP 2ndopinionmd$ export OPENAI_API_KEY=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
www:2ndOpinionMD-MVP 2ndopinionmd$ ./RUN_POSTGRES_APP.sh
🚀 Starting FastAPI application on http://0.0.0.0:8000
📚 API documentation available at: http://0.0.0.0:8000/docs
Database connection will be initialized during FastAPI lifespan startup
2026-02-02 17:05:53,986 - root - INFO - Encrypted logging initialized. Log file: ./logs/server.log
2026-02-02 17:05:54,461 - server.api.kg - INFO - kg.py loaded. OPENAI_API_KEY set: yes
2026-02-02 17:05:54,461 - root - INFO - VALYU_API_KEY present: False tail=None
INFO:     Started server process [3170]
INFO:     Waiting for application startup.
ERROR:    Traceback (most recent call last):
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/starlette/routing.py", line 734, in lifespan
    async with self.lifespan_context(app) as maybe_state:
               ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.12/3.12.12/Frameworks/Python.framework/Versions/3.12/lib/python3.12/contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/server/api/app_postgres.py", line 110, in lifespan
    raise RuntimeError("No DATABASE_URL or SYNC_DATABASE_URL set in environment")
RuntimeError: No DATABASE_URL or SYNC_DATABASE_URL set in environment

ERROR:    Application startup failed. Exiting.
www:2ndOpinionMD-MVP 2ndopinionmd$ # From 2ndOpinionMD-MVP (or PortalVision repo root). Adjust user/password/host if needed.
www:2ndOpinionMD-MVP 2ndopinionmd$ export DATABASE_URL="postgresql+asyncpg://2ndopinionmd@localhost:5432/2ndopinionmd"
www:2ndOpinionMD-MVP 2ndopinionmd$ export SYNC_DATABASE_URL="postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"
www:2ndOpinionMD-MVP 2ndopinionmd$ ./RUN_POSTGRES_APP.sh
🚀 Starting FastAPI application on http://0.0.0.0:8000
📚 API documentation available at: http://0.0.0.0:8000/docs
Database connection will be initialized during FastAPI lifespan startup
2026-02-02 17:06:56,810 - root - INFO - Encrypted logging initialized. Log file: ./logs/server.log
2026-02-02 17:06:57,284 - server.api.kg - INFO - kg.py loaded. OPENAI_API_KEY set: yes
2026-02-02 17:06:57,284 - root - INFO - VALYU_API_KEY present: False tail=None
INFO:     Started server process [3402]
INFO:     Waiting for application startup.
ERROR:    Traceback (most recent call last):
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/.BeatingHeart/lib/python3.12/site-packages/starlette/routing.py", line 734, in lifespan
    async with self.lifespan_context(app) as maybe_state:
               ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.12/3.12.12/Frameworks/Python.framework/Versions/3.12/lib/python3.12/contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/server/api/app_postgres.py", line 110, in lifespan
    raise RuntimeError("No DATABASE_URL or SYNC_DATABASE_URL set in environment")
RuntimeError: No DATABASE_URL or SYNC_DATABASE_URL set in environment

ERROR:    Application startup failed. Exiting.
www:2ndOpinionMD-MVP 2ndopinionmd$ ./RUN_POSTGRES_APP.sh
🚀 Starting FastAPI application on http://0.0.0.0:8000
📚 API documentation available at: http://0.0.0.0:8000/docs
Database connection will be initialized during FastAPI lifespan startup
2026-02-02 17:07:53,484 - root - INFO - Encrypted logging initialized. Log file: ./logs/server.log
2026-02-02 17:07:53,978 - server.api.kg - INFO - kg.py loaded. OPENAI_API_KEY set: yes
2026-02-02 17:07:53,978 - root - INFO - VALYU_API_KEY present: False tail=None
INFO:     Started server process [3625]
INFO:     Waiting for application startup.
2026-02-02 17:07:54,063 - server.api.app_postgres - INFO - Using async DATABASE_URL: postgresql+asyncpg://2ndopinionmd@localhost:5432/2ndopinionmd
2026-02-02 17:07:54,107 - server.api.app_postgres - INFO - Database connection initialized successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)