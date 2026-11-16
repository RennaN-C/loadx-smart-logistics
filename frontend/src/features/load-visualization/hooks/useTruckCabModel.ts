import { useEffect, useState } from "react";
import { MeshPhysicalMaterial, MeshStandardMaterial } from "three";
import type { Group, Mesh, Object3D } from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

import { CAB_MODEL_URL } from "../components/truckCabModel";

/**
 * Carrega a cabine uma única vez por sessão.
 *
 * Cabe a mesma conta que mantém o caminhão desenhado em código: o arquivo tem
 * 1,3 MB e abrir a visualização é coisa que se faz várias vezes seguidas,
 * comparando planos. Descartar ao desmontar devolveria memória de GPU, mas
 * cobraria download e parse de novo a cada abertura. Como é UM modelo pequeno
 * e só, ele fica.
 */
let cache: Promise<Group> | null = null;

function carregar(): Promise<Group> {
  cache ??= new GLTFLoader().loadAsync(CAB_MODEL_URL).then((gltf) => {
    const paints = new Map<MeshStandardMaterial, MeshPhysicalMaterial>();
    gltf.scene.traverse((objeto: Object3D) => {
      const malha = objeto as Mesh;
      if (malha.isMesh) {
        const materials = Array.isArray(malha.material) ? malha.material : [malha.material];
        const refined = materials.map((material) => {
          if (material instanceof MeshStandardMaterial && material.name === "col_kaca") {
            material.color.set("#203345");
            material.metalness = 0.65;
            material.roughness = 0.06;
          }
          if (!(material instanceof MeshStandardMaterial) || material.name !== "col_body") return material;
          let paint = paints.get(material);
          if (!paint) {
            paint = new MeshPhysicalMaterial();
            MeshStandardMaterial.prototype.copy.call(paint, material);
            paint.clearcoat = 1;
            paint.clearcoatRoughness = 0.18;
            paint.roughness = 0.28;
            paints.set(material, paint);
          }
          return paint;
        });
        malha.material = Array.isArray(malha.material) ? refined : refined[0];
        malha.castShadow = true;
        malha.receiveShadow = true;
      }
    });
    paints.forEach((_, original) => original.dispose());
    return gltf.scene;
  });

  return cache;
}

/**
 * `null` enquanto carrega e também se falhar.
 *
 * Falha aqui não é erro de tela: o caminhão continua inteiro, só com a cabine
 * desenhada em código. Por isso não há aviso nem botão de nova tentativa — não
 * há nada que o usuário possa fazer, e a carga, que é o assunto da tela,
 * continua correta.
 */
export function useTruckCabModel(): Group | null {
  const [modelo, setModelo] = useState<Group | null>(null);

  useEffect(() => {
    let vivo = true;

    carregar()
      .then((cena) => {
        // Scene nodes cannot have two parents. Clone the graph per viewer;
        // immutable geometry/materials stay shared with the bounded GLB cache.
        if (vivo) setModelo(cena.clone(true));
      })
      .catch(() => {
        // silêncio proposital: ver o comentário acima
        cache = null;
      });

    return () => {
      vivo = false;
    };
  }, []);

  return modelo;
}
