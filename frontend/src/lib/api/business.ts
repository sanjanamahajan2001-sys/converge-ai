import { request } from './client';
import {
  BusinessOffering,
  BusinessOfferingInput,
  BusinessProfile,
  BusinessProfileUpdate,
  BusinessRequirement,
  BusinessRequirementInput,
  ProductTaxonomyDTO,
  ServiceTaxonomyDTO,
} from '@/types/business';

export async function getMyBusinessProfile(): Promise<BusinessProfile> {
  return request<BusinessProfile>('/business/profile/me');
}

export async function updateMyBusinessProfile(payload: BusinessProfileUpdate): Promise<BusinessProfile> {
  return request<BusinessProfile>('/business/profile/me', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function createOffering(payload: BusinessOfferingInput): Promise<BusinessOffering> {
  return request<BusinessOffering>('/business/offerings', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateOffering(id: string, payload: Partial<BusinessOfferingInput>): Promise<BusinessOffering> {
  return request<BusinessOffering>(`/business/offerings/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteOffering(id: string): Promise<void> {
  return request<void>(`/business/offerings/${id}`, {
    method: 'DELETE',
  });
}

export async function confirmOffering(id: string): Promise<BusinessOffering> {
  return request<BusinessOffering>(`/business/offerings/${id}/confirm`, {
    method: 'POST',
  });
}

export async function createRequirement(payload: BusinessRequirementInput): Promise<BusinessRequirement> {
  return request<BusinessRequirement>('/business/requirements', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateRequirement(id: string, payload: Partial<BusinessRequirementInput>): Promise<BusinessRequirement> {
  return request<BusinessRequirement>(`/business/requirements/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteRequirement(id: string): Promise<void> {
  return request<void>(`/business/requirements/${id}`, {
    method: 'DELETE',
  });
}

export async function getProductTaxonomies(): Promise<ProductTaxonomyDTO[]> {
  return request<ProductTaxonomyDTO[]>('/business/taxonomies/products');
}

export async function getServiceTaxonomies(): Promise<ServiceTaxonomyDTO[]> {
  return request<ServiceTaxonomyDTO[]>('/business/taxonomies/services');
}

import type {
  BusinessMatchSearchRequest,
  BusinessMatchSearchResponse,
  ParsedBusinessRequirement,
} from '@/types/business';

export async function searchBusinessMatches(
  payload: BusinessMatchSearchRequest
): Promise<BusinessMatchSearchResponse> {
  return request<BusinessMatchSearchResponse>('/business/matching/search', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function parseBusinessQuery(
  query: string
): Promise<ParsedBusinessRequirement> {
  return request<ParsedBusinessRequirement>('/business/matching/parse-query', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });
}

export async function getMyActiveRequirements(): Promise<BusinessRequirement[]> {
  return request<BusinessRequirement[]>('/business/matching/my-requirements');
}

export async function getMyActiveOfferings(): Promise<BusinessOffering[]> {
  return request<BusinessOffering[]>('/business/matching/my-offerings');
}
