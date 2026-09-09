export interface Product {
  id: string;
  code: string;
  name: string;
  description: string | null;
  widthCm: number;
  heightCm: number;
  lengthCm: number;
  weightKg: number;
  /** Flags que o otimizador usa para decidir posição, rotação e empilhamento. */
  fragile: boolean;
  stackable: boolean;
  rotationAllowed: boolean;
  createdAt: string;
}

export interface ProductInput {
  code: string;
  name: string;
  description: string | null;
  widthCm: number;
  heightCm: number;
  lengthCm: number;
  weightKg: number;
  fragile: boolean;
  stackable: boolean;
  rotationAllowed: boolean;
}

export type ProductUpdateInput = Partial<ProductInput>;
