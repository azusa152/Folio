/* eslint-disable react-refresh/only-export-components */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { type RenderOptions, render, type RenderResult } from "@testing-library/react"
import type { ReactElement, ReactNode } from "react"
import { MemoryRouter } from "react-router-dom"

type ExtendedRenderOptions = Omit<RenderOptions, "wrapper"> & {
  route?: string
}

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

export function renderWithProviders(
  ui: ReactElement,
  options: ExtendedRenderOptions = {},
): RenderResult & { queryClient: QueryClient } {
  const { route = "/", ...renderOptions } = options
  const queryClient = createTestQueryClient()

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
      </QueryClientProvider>
    )
  }

  return {
    queryClient,
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  }
}

export * from "@testing-library/react"
