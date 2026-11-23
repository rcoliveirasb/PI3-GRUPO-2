// Comunicação com a API de segmentação (pasta pji/ do repositório do projeto).
// Endereço padrão: http://localhost:8000. Para mudar, crie um arquivo .env com
// VITE_API_URL=http://outro-endereco:porta

export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

export const METODOS = [
  { id: 'baseline', nome: 'Baseline', cor: [255, 140, 0] },
  { id: 'region_growing', nome: 'Region growing', cor: [80, 170, 255] },
  { id: 'unet', nome: 'U-Net 2D', cor: [60, 210, 120] },
]

// Como cada modo da API aparece na tela (o vídeo precisa deixar claro de onde vêm os números).
export const NOMES_MODO = {
  valores_fixos: 'Valores de exemplo (não são resultados reais)',
  pre_calculado: 'Resultados reais pré-calculados (Teste A)',
  modelo_real: 'Modelo rodando ao vivo',
}

async function pedir(caminho) {
  const resposta = await fetch(`${API_URL}${caminho}`)
  if (!resposta.ok) {
    let detalhe = ''
    try { detalhe = (await resposta.json())?.detail?.mensagem ?? '' } catch { /* resposta sem JSON */ }
    throw new Error(detalhe || `Erro ${resposta.status} em ${caminho}`)
  }
  return resposta.json()
}

export async function verificarApi() {
  return pedir('/saude')
}

export async function listarExames() {
  return (await pedir('/exames')).exames
}

// Roda (ou busca do cache da API) os três métodos para um exame.
// Devolve { fatia: {indice, url}, metodos: { baseline: {metricas, mascaraUrl}, ... } }
export async function segmentarTodos(exameId) {
  const respostas = await Promise.all(
    METODOS.map(m => pedir(`/exames/${encodeURIComponent(exameId)}/segmentacao/${m.id}`)),
  )
  const metodos = {}
  respostas.forEach((r, i) => {
    metodos[METODOS[i].id] = { metricas: r.metricas, mascaraUrl: `${API_URL}${r.mascara.url}` }
  })
  return {
    fatia: { indice: respostas[0].fatia.indice, url: `${API_URL}${respostas[0].fatia.url}` },
    metodos,
  }
}
