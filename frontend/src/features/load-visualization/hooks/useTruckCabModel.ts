import { useEffect, useState } from "react";
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
    gltf.scene.traverse((objeto: Object3D) => {
      const malha = objeto as Mesh;
      if (malha.isMesh) {
        malha.castShadow = true;
        malha.receiveShadow = true;
      }
    });
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
        if (vivo) setModelo(cena);
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
