import { Texture } from "three";
import { describe, expect, it, vi } from "vitest";
import { createSceneResources } from "./sceneResources";

describe("scene resource ownership", () => {
  it("shares a unit geometry and bounded materials across 200 volume instances", () => {
    const resources = createSceneResources();
    const textures = Array.from({ length: 6 }, () => new Texture());
    const solid = resources.cargoMaterials(textures, false);
    const dimmed = resources.cargoMaterials(textures, true);
    for (let index = 0; index < 200; index += 1) {
      expect(resources.cargoMaterials(textures, false)).toBe(solid);
      expect(resources.cargoMaterials(textures, true)).toBe(dimmed);
    }
    expect(solid).toHaveLength(6);
    expect(dimmed).toHaveLength(6);
    expect(dimmed[0]).not.toBe(solid[0]);
    expect(solid[0].map).toBe(textures[0]);
    expect(dimmed[0].depthWrite).toBe(false);
    expect(resources.unitBox.parameters).toMatchObject({ width: 1, height: 1, depth: 1 });
    resources.dispose();
    textures.forEach((texture) => texture.dispose());
  });

  it("disposes its geometry and material variants while preserving shared texture ownership", () => {
    const resources = createSceneResources();
    const texture = new Texture();
    const faces = [texture, null, null, null, null, null];
    const solid = resources.cargoMaterials(faces, false);
    const dimmed = resources.cargoMaterials(faces, true);
    const textureDispose = vi.spyOn(texture, "dispose");
    const boxDispose = vi.spyOn(resources.unitBox, "dispose");
    const edgesDispose = vi.spyOn(resources.unitEdges, "dispose");
    const materialDisposals = [...solid, ...dimmed].map((material) => vi.spyOn(material, "dispose"));
    resources.dispose();
    expect(boxDispose).toHaveBeenCalledOnce();
    expect(edgesDispose).toHaveBeenCalledOnce();
    materialDisposals.forEach((dispose) => expect(dispose).toHaveBeenCalledOnce());
    expect(textureDispose).not.toHaveBeenCalled();
    texture.dispose();
  });

  it("keeps scene-owned materials independent when switching vehicles", () => {
    const first = createSceneResources();
    const second = createSceneResources();
    const faces = [new Texture()];
    const firstMaterials = first.cargoMaterials(faces, false);
    const secondMaterials = second.cargoMaterials(faces, false);
    const secondDispose = vi.spyOn(secondMaterials[0], "dispose");
    expect(second.unitBox).not.toBe(first.unitBox);
    expect(secondMaterials[0]).not.toBe(firstMaterials[0]);
    first.dispose();
    expect(secondDispose).not.toHaveBeenCalled();
    second.dispose();
    faces[0].dispose();
  });
});
