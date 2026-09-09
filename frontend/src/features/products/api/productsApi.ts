import { api } from "../../../services/api";
import { mapPageFromDto, toPageQuery, type ListParams, type PageDto } from "../../../services/pagination";
import type { Page } from "../../../types/api";
import type { Product, ProductInput, ProductUpdateInput } from "../types";

interface ProductDto {
  id: string;
  code: string;
  name: string;
  description: string | null;
  width_cm: number;
  height_cm: number;
  length_cm: number;
  weight_kg: number;
  fragile: boolean;
  stackable: boolean;
  rotation_allowed: boolean;
  created_at: string;
}

export function mapProductFromDto(dto: ProductDto): Product {
  return {
    id: dto.id,
    code: dto.code,
    name: dto.name,
    description: dto.description,
    widthCm: dto.width_cm,
    heightCm: dto.height_cm,
    lengthCm: dto.length_cm,
    weightKg: dto.weight_kg,
    fragile: dto.fragile,
    stackable: dto.stackable,
    rotationAllowed: dto.rotation_allowed,
    createdAt: dto.created_at,
  };
}

function mapProductToDto(input: ProductUpdateInput): Partial<ProductDto> {
  const dto: Partial<ProductDto> = {};

  if (input.code !== undefined) dto.code = input.code;
  if (input.name !== undefined) dto.name = input.name;
  if (input.description !== undefined) dto.description = input.description;
  if (input.widthCm !== undefined) dto.width_cm = input.widthCm;
  if (input.heightCm !== undefined) dto.height_cm = input.heightCm;
  if (input.lengthCm !== undefined) dto.length_cm = input.lengthCm;
  if (input.weightKg !== undefined) dto.weight_kg = input.weightKg;
  if (input.fragile !== undefined) dto.fragile = input.fragile;
  if (input.stackable !== undefined) dto.stackable = input.stackable;
  if (input.rotationAllowed !== undefined) dto.rotation_allowed = input.rotationAllowed;

  return dto;
}

export function mapProductPageFromDto(dto: PageDto<ProductDto>): Page<Product> {
  return mapPageFromDto(dto, mapProductFromDto);
}

export async function listProducts(params: ListParams = {}): Promise<Page<Product>> {
  const { data } = await api.get<PageDto<ProductDto>>("/products", { params: toPageQuery(params) });

  return mapProductPageFromDto(data);
}

export async function createProduct(input: ProductInput): Promise<Product> {
  const { data } = await api.post<ProductDto>("/products", mapProductToDto(input));

  return mapProductFromDto(data);
}

export async function updateProduct(id: string, input: ProductUpdateInput): Promise<Product> {
  const { data } = await api.patch<ProductDto>(`/products/${id}`, mapProductToDto(input));

  return mapProductFromDto(data);
}
