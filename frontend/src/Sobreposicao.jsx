import { useEffect, useRef } from 'react'

function carregarImagem(url) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous' // a API libera CORS; sem isso o canvas não deixa ler os pixels
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error(`Não foi possível carregar ${url}`))
    img.src = url
  })
}

// Desenha a fatia da tomografia e pinta por cima, com a cor do método,
// os pixels que a máscara marca como pulmão (255 = pulmão, 0 = fora).
export default function Sobreposicao({ fatiaUrl, mascaraUrl, cor, titulo }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    let cancelado = false
    Promise.all([carregarImagem(fatiaUrl), carregarImagem(mascaraUrl)]).then(([fatia, mascara]) => {
      if (cancelado || !canvasRef.current) return
      const canvas = canvasRef.current
      canvas.width = fatia.width
      canvas.height = fatia.height
      const ctx = canvas.getContext('2d')
      ctx.drawImage(fatia, 0, 0)

      const temp = document.createElement('canvas')
      temp.width = fatia.width
      temp.height = fatia.height
      const tctx = temp.getContext('2d')
      tctx.drawImage(mascara, 0, 0, fatia.width, fatia.height)
      const pixelsMascara = tctx.getImageData(0, 0, fatia.width, fatia.height).data

      const imagem = ctx.getImageData(0, 0, fatia.width, fatia.height)
      const p = imagem.data
      const alfa = 0.45
      for (let i = 0; i < p.length; i += 4) {
        if (pixelsMascara[i] > 127) {
          p[i] = p[i] * (1 - alfa) + cor[0] * alfa
          p[i + 1] = p[i + 1] * (1 - alfa) + cor[1] * alfa
          p[i + 2] = p[i + 2] * (1 - alfa) + cor[2] * alfa
        }
      }
      ctx.putImageData(imagem, 0, 0)
    }).catch(() => { /* a mensagem de erro aparece no painel principal */ })
    return () => { cancelado = true }
  }, [fatiaUrl, mascaraUrl, cor])

  return <canvas ref={canvasRef} className="sobreposicao-canvas" aria-label={titulo} />
}
