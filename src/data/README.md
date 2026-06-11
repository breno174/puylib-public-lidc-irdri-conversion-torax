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

Para testar a query com filtro `in_` e exportar as 3 primeiras anotacoes como PNG:

```bash
venv/bin/python src/main.py --export-first-annotations
```

Por padrao, esse comando usa scans com `slice_thickness < 1.0`, busca as anotacoes com
`pl.Annotation.scan_id.in_(scan_ids)`, salva as imagens em
`src/data/output/first_annotations/` e cria o CSV
`first_annotations_malignancy.csv`.

Para montar um dataset LIDC-IDRI filtrado por consenso medico, mantendo apenas
nodulos com pelo menos 3 anotacoes no mesmo cluster:

```bash
venv/bin/python src/main.py --export-consensus-annotations --limit 0
```

Esse comando converte os DICOMs para imagens brutas 2D, sem legenda, sem titulo,
sem eixo e sem overlay. Por padrao ele salva a fatia axial inteira (`slice`) em
PNG grayscale 8-bit usando lung window (`center=-600`, `width=1500`). As imagens
e o CSV de metadados ficam em:

```text
src/data/output/consensus_min_3/
  consensus_annotations.csv
  001_LIDC-IDRI-XXXX_cluster_Y_anns_Z.png
  ...
```

Opcoes uteis:

```bash
# Exportar JPEG em vez de PNG
venv/bin/python src/main.py --export-consensus-annotations --limit 0 --image-format jpg

# Exportar recortes dos nodulos em vez da fatia inteira
venv/bin/python src/main.py --export-consensus-annotations --limit 0 --export-scope crop

# Exportar em 3 canais RGB, parecido com datasets de CNN pre-treinada em ImageNet
venv/bin/python src/main.py --export-consensus-annotations --limit 0 --color-mode rgb

# Exigir estritamente mais de 3 anotacoes
venv/bin/python src/main.py --export-consensus-annotations --limit 0 --min-annotations 4
```

O `--write-config` cria o arquivo esperado pelo `pylidc` no diretorio do usuario:

```text
Windows: ~/pylidc.conf
Linux/macOS: ~/.pylidcrc
```
