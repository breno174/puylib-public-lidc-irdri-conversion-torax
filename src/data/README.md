# Dados LIDC-IDRI

Coloque os arquivos DICOM do LIDC-IDRI nesta pasta, mantendo a estrutura esperada pelo
`pylidc`:

```text
src/data/LIDC-IDRI/
  LIDC-IDRI-0001/
  LIDC-IDRI-0002/
  ...
```

O exemplo em `src/main.py` usa `LIDC_DICOM_PATH=src/data/LIDC-IDRI`, definido no arquivo
`.env`, e salva imagens geradas em `src/data/output`.

Depois de preencher os dados, instale as dependencias e gere a configuracao do
`pylidc`.

No Windows:

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe src\main.py --write-config
venv\Scripts\python.exe src\main.py
```

No Linux/macOS:

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
venv/bin/python src/main.py --write-config
venv/bin/python src/main.py
```

O `--write-config` cria o arquivo esperado pelo `pylidc` no diretorio do usuario:

```text
Windows: ~/pylidc.conf
Linux/macOS: ~/.pylidcrc
```
