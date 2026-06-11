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

Depois de preencher os dados, rode:

```powershell
venv\Scripts\python.exe src\main.py --write-config
venv\Scripts\python.exe src\main.py
```


