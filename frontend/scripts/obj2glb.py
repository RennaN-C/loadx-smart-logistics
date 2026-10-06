"""Converte o OBJ do caminhao DAF em GLB enxuto.

Nao existe Blender nem trimesh nesta maquina, entao a conversao e feita aqui:
le o OBJ, descarta o que nao e caminhao, triangula, indexa e escreve o
container GLB (JSON + BIN).

Uso: python obj2glb.py <entrada.obj> <saida.glb> [objetos a excluir...]
"""

import base64
import io
import json
import struct
import sys
from pathlib import Path

# Materiais pintados por NOME, porque o MTL do modelo veio com os 14 materiais
# no mesmo cinza 0.64 e sem nenhum map_Kd. Os nomes (em indonesio) dizem o que
# cada parte e: kaca=vidro, ban=pneu, pelek=roda, besi=metal, lantai=chao.
PALETA = {
    "col_body":            ((0.82, 0.84, 0.86, 1.0), 0.25, 0.35),
    "col_box":             ((0.88, 0.89, 0.90, 1.0), 0.10, 0.45),
    "col_besi_box":        ((0.52, 0.55, 0.58, 1.0), 0.70, 0.40),
    "col_black":           ((0.09, 0.10, 0.11, 1.0), 0.30, 0.60),
    "col_kaca":            ((0.30, 0.38, 0.44, 1.0), 0.05, 0.08),
    "col_ban":             ((0.07, 0.07, 0.08, 1.0), 0.00, 0.92),
    "uv_ban_depan":        ((0.08, 0.08, 0.09, 1.0), 0.00, 0.90),
    "uv_ban_belakang_3":   ((0.08, 0.08, 0.09, 1.0), 0.00, 0.90),
    "uv_col_ban_belakang": ((0.08, 0.08, 0.09, 1.0), 0.00, 0.90),
    "col_pelek":           ((0.74, 0.76, 0.78, 1.0), 0.85, 0.30),
    "col_lamp_red":        ((0.62, 0.09, 0.10, 1.0), 0.00, 0.40),
    "col_light_ban":       ((0.80, 0.78, 0.70, 1.0), 0.00, 0.50),
    "light":               ((0.95, 0.93, 0.86, 1.0), 0.00, 0.35),
    "lantai":              ((0.35, 0.35, 0.36, 1.0), 0.00, 0.80),
}
PADRAO = ((0.70, 0.71, 0.72, 1.0), 0.20, 0.50)

# O conversor é ferramenta de desenvolvimento. Entrada e saída precisam ficar
# no diretório em que ele foi chamado: aceitar caminhos arbitrários pela CLI
# permitiria ler ou sobrescrever arquivos fora do workspace.
WORKSPACE = Path.cwd().resolve()


def caminho_local(valor, *, precisa_existir):
    caminho = (WORKSPACE / valor).resolve()

    try:
        caminho.relative_to(WORKSPACE)
    except ValueError as exc:
        raise ValueError(
            f"caminho fora do diretório de trabalho: {valor}"
        ) from exc

    if precisa_existir and not caminho.is_file():
        raise FileNotFoundError(f"arquivo de entrada não encontrado: {valor}")

    return caminho


def ler_obj(caminho, excluir):
    pos, nor, uvs = [], [], []
    # (material -> lista de triangulos); cada canto e (ip, iuv, inor)
    grupos = {}
    objeto, material = None, "padrao"
    pulando = False

    with io.open(caminho, encoding="utf-8", errors="ignore") as f:
        for linha in f:
            if linha.startswith("v "):
                p = linha.split()
                pos.append((float(p[1]), float(p[2]), float(p[3])))
            elif linha.startswith("vn "):
                p = linha.split()
                nor.append((float(p[1]), float(p[2]), float(p[3])))
            elif linha.startswith("vt "):
                p = linha.split()
                uvs.append((float(p[1]), float(p[2])))
            elif linha.startswith("o "):
                objeto = linha[2:].strip()
                pulando = objeto in excluir
            elif linha.startswith("usemtl "):
                material = linha[7:].strip()
            elif linha.startswith("f ") and not pulando:
                cantos = []
                for parte in linha.split()[1:]:
                    campos = (parte.split("/") + ["", ""])[:3]
                    ip = int(campos[0]) - 1
                    iuv = int(campos[1]) - 1 if campos[1] else -1
                    ino = int(campos[2]) - 1 if campos[2] else -1
                    cantos.append((ip, iuv, ino))
                # leque: o OBJ traz quadrilateros e alguns octogonos, e glTF so
                # aceita triangulo
                for i in range(1, len(cantos) - 1):
                    grupos.setdefault(material, []).append(
                        (cantos[0], cantos[i], cantos[i + 1])
                    )
    return pos, nor, uvs, grupos


def indexar(grupos, pos, nor, desloc):
    """Um buffer por material, deduplicando o trio (posicao, uv, normal)."""
    saida = []
    dx, dy, dz = desloc
    for material, tris in grupos.items():
        mapa, vp, vn, vt, idx = {}, [], [], [], []
        for tri in tris:
            for canto in tri:
                chave = (canto[0], canto[2])
                achado = mapa.get(chave)
                if achado is None:
                    achado = len(vp)
                    mapa[chave] = achado
                    x, y, z = pos[canto[0]]
                    vp.append((x + dx, y + dy, z + dz))
                    vn.append(nor[canto[2]] if canto[2] >= 0 else (0.0, 1.0, 0.0))
                idx.append(achado)
        saida.append((material, vp, vn, vt, idx))
    return saida


def escrever_glb(primitivas, destino):
    buf = bytearray()
    vistas, acessores, materiais, indices_mat, prims = [], [], [], {}, []

    def alinhar():
        while len(buf) % 4:
            buf.append(0)

    def vista(dados, alvo):
        alinhar()
        inicio = len(buf)
        buf.extend(dados)
        vistas.append({"buffer": 0, "byteOffset": inicio,
                       "byteLength": len(dados), "target": alvo})
        return len(vistas) - 1

    for material, vp, vn, vt, idx in primitivas:
        if material not in indices_mat:
            cor, metal, rugos = PALETA.get(material, PADRAO)
            indices_mat[material] = len(materiais)
            materiais.append({
                "name": material,
                "pbrMetallicRoughness": {
                    "baseColorFactor": list(cor),
                    "metallicFactor": metal,
                    "roughnessFactor": rugos,
                },
                "doubleSided": True,
            })

        bv_p = vista(struct.pack(f"<{len(vp) * 3}f", *[c for v in vp for c in v]), 34962)
        bv_n = vista(struct.pack(f"<{len(vn) * 3}f", *[c for v in vn for c in v]), 34962)
        # Indice de 16 bits quando cabe: metade do tamanho, e a maioria das
        # primitivas tem bem menos que 65536 vertices.
        curto = len(vp) < 65536
        formato = "H" if curto else "I"
        bv_i = vista(struct.pack(f"<{len(idx)}{formato}", *idx), 34963)

        minimo = [min(v[i] for v in vp) for i in range(3)]
        maximo = [max(v[i] for v in vp) for i in range(3)]

        base = len(acessores)
        acessores.append({"bufferView": bv_p, "componentType": 5126, "count": len(vp),
                          "type": "VEC3", "min": minimo, "max": maximo})
        acessores.append({"bufferView": bv_n, "componentType": 5126, "count": len(vn),
                          "type": "VEC3"})
        acessores.append({"bufferView": bv_i, "componentType": 5123 if curto else 5125,
                          "count": len(idx), "type": "SCALAR"})

        prims.append({
            "attributes": {"POSITION": base, "NORMAL": base + 1},
            "indices": base + 2,
            "material": indices_mat[material],
        })

    alinhar()
    gltf = {
        "asset": {"version": "2.0", "generator": "LoadX obj2glb"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "truck_daf"}],
        "meshes": [{"name": "truck_daf", "primitives": prims}],
        "materials": materiais,
        "accessors": acessores,
        "bufferViews": vistas,
        "buffers": [{"byteLength": len(buf)}],
    }

    json_bin = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_bin += b" " * ((4 - len(json_bin) % 4) % 4)

    total = 12 + 8 + len(json_bin) + 8 + len(buf)
    with io.open(destino, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(json_bin), 0x4E4F534A))
        f.write(json_bin)
        f.write(struct.pack("<II", len(buf), 0x004E4942))
        f.write(buf)

    return total, len(materiais), sum(len(p[4]) for p in primitivas) // 3


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(
            "uso: python obj2glb.py <entrada.obj> <saida.glb> [objetos a excluir...]"
        )

    entrada = caminho_local(sys.argv[1], precisa_existir=True)
    saida = caminho_local(sys.argv[2], precisa_existir=False)
    excluir = set(sys.argv[3:])

    pos, nor, uvs, grupos = ler_obj(entrada, excluir)

    # Normaliza: X centrado, Y zerado no chao, Z comecando em zero. Assim o
    # componente React posiciona por dimensao, nao por numero magico.
    usados = {c[0] for tris in grupos.values() for tri in tris for c in tri}
    xs = [pos[i][0] for i in usados]
    ys = [pos[i][1] for i in usados]
    zs = [pos[i][2] for i in usados]
    desloc = (-(min(xs) + max(xs)) / 2, -min(ys), -min(zs))

    prims = indexar(grupos, pos, nor, desloc)
    total, n_mat, n_tri = escrever_glb(prims, saida)

    print(f"saida ......: {saida}")
    print(f"tamanho ....: {total / 1_048_576:.2f} MB")
    print(f"triangulos .: {n_tri}")
    print(f"materiais ..: {n_mat}")
    print(f"dimensoes ..: X={max(xs) - min(xs):.3f} Y={max(ys) - min(ys):.3f} Z={max(zs) - min(zs):.3f}")
