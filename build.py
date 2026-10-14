"""Gera index.html (site completo, GitHub Pages) e _preview.html (corpo para a prévia no Claude) a partir de src/body.html."""
import base64
from pathlib import Path
R = Path(__file__).resolve().parent
corpo = (R / 'src/body.html').read_text().replace('{{HDL_THUMB}}', base64.b64encode((R / 'assets/hdl_video.jpg').read_bytes()).decode())
(R / '_preview.html').write_text(corpo)
(R / 'index.html').write_text('<!doctype html>\n<html lang="pt-BR" data-lang="pt">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n</head>\n<body>\n' + corpo + '\n</body>\n</html>\n')
print('ok')
