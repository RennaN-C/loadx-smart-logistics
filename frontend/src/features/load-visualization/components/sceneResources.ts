import { BoxGeometry, EdgesGeometry, MeshLambertMaterial, MeshStandardMaterial, type Texture } from "three";

/** One unit box and one outline per scene; scale preserves the API dimensions. */
export function createSceneResources() {
  const unitBox = new BoxGeometry(1, 1, 1);
  const unitEdges = new EdgesGeometry(unitBox);
  const materials = new Map<readonly (Texture | null)[], Map<boolean, MeshStandardMaterial[]>>();
  const flatMaterials = new Map<string, MeshLambertMaterial>();

  return {
    unitBox,
    unitEdges,
    flatCargoMaterial(color: string, dimmed: boolean) {
      const key = `${color}:${dimmed}`;
      let material = flatMaterials.get(key);
      if (!material) {
        material = new MeshLambertMaterial({ color, transparent: dimmed, opacity: dimmed ? 0.1 : 1, depthWrite: !dimmed });
        flatMaterials.set(key, material);
      }
      return material;
    },
    cargoMaterials(faces: readonly (Texture | null)[], dimmed: boolean) {
      let variants = materials.get(faces);
      if (!variants) {
        variants = new Map();
        materials.set(faces, variants);
      }
      let result = variants.get(dimmed);
      if (!result) {
        result = faces.map((texture) => new MeshStandardMaterial({
          map: texture,
          bumpMap: texture,
          bumpScale: 0.008,
          roughness: 0.86,
          metalness: 0,
          transparent: dimmed,
          opacity: dimmed ? 0.1 : 1,
          depthWrite: !dimmed,
        }));
        variants.set(dimmed, result);
      }
      return result;
    },
    dispose() {
      unitEdges.dispose();
      unitBox.dispose();
      for (const material of flatMaterials.values()) material.dispose();
      for (const variants of materials.values()) {
        for (const variant of variants.values()) {
          for (const material of variant) material.dispose();
        }
      }
      // Textures belong to the bounded cargoTexture cache, not this scene.
    },
  };
}

export type SceneResources = ReturnType<typeof createSceneResources>;
