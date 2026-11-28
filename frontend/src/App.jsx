import { useEffect, useRef, useState } from 'react'
import './App.css'
import { API_URL, FORMATOS_ENVIO, METODOS, NOMES_MODO, analisarArquivo, listarExames, segmentarTodos, verificarApi } from './api'
import Sobreposicao from './Sobreposicao'

function formatar(numero, casas = 3) {
  if (numero === null || numero === undefined) return '—'
  return Number(numero).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })
}

const pacientesIniciais = [
  { id: 1, nome: 'Maria Silva', peso: '65', observacoes: 'Acompanhamento de rotina', exames: [
    { id: 101, nome: 'Exame_01', data: '10/09/2026', arquivo: null, status: 'Aguardando arquivo', fatia: 1 },
    { id: 102, nome: 'Exame_02', data: '15/09/2026', arquivo: null, status: 'Aguardando arquivo', fatia: 1 },
  ], exameAtivoId: 101 },
  { id: 2, nome: 'João Santos', peso: '78', observacoes: 'Sem observações registradas', exames: [
    { id: 201, nome: 'Exame_01', data: '12/09/2026', arquivo: null, status: 'Aguardando arquivo', fatia: 1 },
  ], exameAtivoId: 201 },
  { id: 3, nome: 'Ana Oliveira', peso: '59', observacoes: 'Avaliação inicial', exames: [
    { id: 301, nome: 'Exame_01', data: '18/09/2026', arquivo: null, status: 'Aguardando arquivo', fatia: 1 },
    { id: 302, nome: 'Exame_02', data: '25/09/2026', arquivo: null, status: 'Aguardando arquivo', fatia: 1 },
    { id: 303, nome: 'Exame_03', data: '02/10/2026', arquivo: null, status: 'Aguardando arquivo', fatia: 1 },
  ], exameAtivoId: 301 },
]

function UserIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="7" r="3.5" /><path d="M5 20v-2a7 7 0 0 1 14 0v2z" /></svg>
}

function App() {
  const [pacientes, setPacientes] = useState(pacientesIniciais)
  const [abasAbertas, setAbasAbertas] = useState(pacientesIniciais.map(p => p.id))
  const [pacienteAtivoId, setPacienteAtivoId] = useState(1)
  const [historicoAberto, setHistoricoAberto] = useState(false)
  const [configAberta, setConfigAberta] = useState(false)
  const [busca, setBusca] = useState('')
  const [mostrarNovoPaciente, setMostrarNovoPaciente] = useState(false)
  const [nomeNovoPaciente, setNomeNovoPaciente] = useState('')
  const [pesoNovoPaciente, setPesoNovoPaciente] = useState('')
  const [observacoesNovoPaciente, setObservacoesNovoPaciente] = useState('')
  const [mensagem, setMensagem] = useState('')
  const inputArquivoRef = useRef(null)
  // Conexão com a API de segmentação
  const [examesApi, setExamesApi] = useState([])
  const [estadoApi, setEstadoApi] = useState({ conectada: false, modo: null, erro: null })
  const [segmentando, setSegmentando] = useState(false)

  useEffect(() => {
    Promise.all([verificarApi(), listarExames()])
      .then(([saude, exames]) => {
        setEstadoApi({ conectada: true, modo: saude.modo, erro: null })
        setExamesApi(exames.filter(e => e.baixado !== false))
      })
      .catch(() => setEstadoApi({ conectada: false, modo: null, erro: `API fora do ar em ${API_URL}` }))
  }, [])

  const pacienteAtivo = pacientes.find(p => p.id === pacienteAtivoId) ?? pacientes.find(p => abasAbertas.includes(p.id)) ?? null
  const exameAtivo = pacienteAtivo ? (pacienteAtivo.exames.find(e => e.id === pacienteAtivo.exameAtivoId) ?? pacienteAtivo.exames[0]) : null
  const indiceExame = pacienteAtivo && exameAtivo ? pacienteAtivo.exames.findIndex(e => e.id === exameAtivo.id) : -1
  // Resultado veio de um arquivo enviado (POST /analises), não de um exame do servidor
  const porEnvio = exameAtivo?.resultado?.origem === 'envio'
  const pacientesFiltrados = pacientes.filter(p => p.nome.toLowerCase().includes(busca.toLowerCase()))

  function atualizarExameAtual(mudancas) {
    setPacientes(atuais => atuais.map(p => p.id !== pacienteAtivoId ? p : {
      ...p,
      exames: p.exames.map(e => e.id === exameAtivo.id ? { ...e, ...mudancas } : e),
    }))
  }

  // Atualiza um exame pelos ids (seguro depois de um await, mesmo se o usuário trocou de aba)
  function atualizarExame(pacienteId, exameId, mudancas) {
    setPacientes(atuais => atuais.map(p => p.id !== pacienteId ? p : {
      ...p,
      exames: p.exames.map(e => e.id === exameId ? { ...e, ...mudancas } : e),
    }))
  }

  function escolherExameApi(exameApiId) {
    atualizarExameAtual({
      exameApiId: exameApiId || null,
      arquivo: exameApiId ? null : exameAtivo.arquivo,
      resultado: null,
      status: exameApiId ? 'Tomografia selecionada' : 'Aguardando arquivo',
      fatia: 1,
    })
    setMensagem('')
  }

  async function iniciarSegmentacao() {
    if (!exameAtivo?.exameApiId && !exameAtivo?.arquivo) {
      setMensagem('Envie uma fatia de tomografia (.png, .jpg ou .dcm) ou escolha uma tomografia do servidor.')
      return
    }
    const pacienteId = pacienteAtivo.id
    const exameId = exameAtivo.id
    const enviando = !exameAtivo.exameApiId
    setSegmentando(true)
    atualizarExame(pacienteId, exameId, { status: 'Segmentando...' })
    setMensagem(enviando
      ? `Analisando ${exameAtivo.arquivo.name} com baseline, region growing e U-Net...`
      : 'Rodando baseline, region growing e U-Net...')
    try {
      const resultado = enviando
        ? await analisarArquivo(exameAtivo.arquivo)
        : await segmentarTodos(exameAtivo.exameApiId)
      atualizarExame(pacienteId, exameId, { resultado, status: 'Segmentação concluída', fatia: resultado.fatia.indice ?? 1 })
      setMensagem(enviando
        ? 'Análise concluída: a imagem enviada passou pelos três métodos.'
        : 'Segmentação concluída: os três métodos lado a lado.')
    } catch (erro) {
      atualizarExame(pacienteId, exameId, { status: 'Erro na segmentação' })
      setMensagem(`Não foi possível segmentar: ${erro.message}`)
    } finally {
      setSegmentando(false)
    }
  }

  function atualizarPacienteAtual(campo, valor) {
    setPacientes(atuais => atuais.map(p => p.id === pacienteAtivoId ? { ...p, [campo]: valor } : p))
  }

  function selecionarPaciente(id) {
    setAbasAbertas(atuais => atuais.includes(id) ? atuais : [...atuais, id])
    setPacienteAtivoId(id)
    setHistoricoAberto(false)
    setMensagem('')
  }

  function fecharAbaPaciente(id) {
    const restantes = abasAbertas.filter(abaId => abaId !== id)
    if (restantes.length === 0) {
      setMensagem('Mantenha pelo menos uma aba de paciente aberta.')
      return
    }
    setAbasAbertas(restantes)
    if (pacienteAtivoId === id) setPacienteAtivoId(restantes[restantes.length - 1])
    setMensagem('Aba fechada. O paciente continua disponível no histórico.')
  }

  function mudarExame(direcao) {
    const novoIndice = Math.max(0, Math.min(pacienteAtivo.exames.length - 1, indiceExame + direcao))
    const novoExame = pacienteAtivo.exames[novoIndice]
    atualizarPacienteAtual('exameAtivoId', novoExame.id)
    setMensagem('')
  }

  function criarNovoExame() {
    const novoId = Date.now()
    const novoExame = {
      id: novoId,
      nome: `Exame_${String(pacienteAtivo.exames.length + 1).padStart(2, '0')}`,
      data: new Date().toLocaleDateString('pt-BR'),
      arquivo: null,
      status: 'Aguardando arquivo',
      fatia: 1,
    }
    setPacientes(atuais => atuais.map(p => p.id !== pacienteAtivoId ? p : {
      ...p, exames: [...p.exames, novoExame], exameAtivoId: novoId,
    }))
    setMensagem(`Novo exame criado para ${pacienteAtivo.nome}.`)
  }

  function selecionarArquivo(event) {
    const selecionado = event.target.files?.[0]
    if (!selecionado) return
    atualizarExameAtual({ arquivo: selecionado, exameApiId: null, resultado: null, status: 'Arquivo selecionado', fatia: 1 })
    setMensagem(`${selecionado.name} pronto. Clique em “Iniciar segmentação” para analisar.`)
    event.target.value = ''
  }

  function soltarArquivo(event) {
    event.preventDefault()
    const dropped = event.dataTransfer.files?.[0]
    if (!dropped) return
    atualizarExameAtual({ arquivo: dropped, exameApiId: null, resultado: null, status: 'Arquivo selecionado', fatia: 1 })
    setMensagem(`${dropped.name} pronto. Clique em “Iniciar segmentação” para analisar.`)
  }

  function criarPaciente(event) {
    event.preventDefault()
    const nome = nomeNovoPaciente.trim()
    if (!nome) return
    const id = Date.now()
    const exameId = id + 1
    const novoPaciente = {
      id, nome, peso: pesoNovoPaciente, observacoes: observacoesNovoPaciente,
      exames: [{ id: exameId, nome: 'Exame_01', data: new Date().toLocaleDateString('pt-BR'), arquivo: null, status: 'Aguardando arquivo', fatia: 1 }],
      exameAtivoId: exameId,
    }
    setPacientes(atuais => [...atuais, novoPaciente])
    setAbasAbertas(atuais => [...atuais, id])
    setPacienteAtivoId(id)
    setMostrarNovoPaciente(false)
    setNomeNovoPaciente('')
    setPesoNovoPaciente('')
    setObservacoesNovoPaciente('')
    setHistoricoAberto(false)
    setMensagem('Paciente criado. O primeiro exame está pronto para receber uma tomografia.')
  }

  function salvarResultado() {
    if (!pacienteAtivo || !exameAtivo) return
    const resultado = {
      paciente: { nome: pacienteAtivo.nome, peso: pacienteAtivo.peso, observacoes: pacienteAtivo.observacoes },
      exame: {
        nome: exameAtivo.nome, data: exameAtivo.data, arquivo: exameAtivo.arquivo?.name ?? null,
        status: exameAtivo.status, fatia: exameAtivo.fatia,
        tomografiaServidor: exameAtivo.exameApiId ?? null,
        resultadosSegmentacao: exameAtivo.resultado
          ? Object.fromEntries(Object.entries(exameAtivo.resultado.metodos).map(([m, r]) => [m, r.metricas]))
          : null,
      },
      origemDosResultados: estadoApi.modo ? NOMES_MODO[estadoApi.modo] ?? estadoApi.modo : null,
      aviso: 'Protótipo acadêmico. Não é um dispositivo médico e não deve ser usado para diagnóstico.',
    }
    const blob = new Blob([JSON.stringify(resultado, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${pacienteAtivo.nome.replace(/\s+/g, '_')}_${exameAtivo.nome}.json`
    link.click()
    URL.revokeObjectURL(url)
    setMensagem(exameAtivo.resultado ? 'Resultado salvo em JSON.' : 'Resumo salvo em JSON (ainda sem segmentação).')
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="logo">Pulmo Scan</h1>
        <div className="separador" />
        <button className={`icone-pacientes ${historicoAberto ? 'selecionado' : ''}`} title="Histórico de pacientes" aria-label="Abrir histórico de pacientes" onClick={() => { setHistoricoAberto(v => !v); setConfigAberta(false) }}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="7" r="3.2" /><path d="M2.8 19v-1.8a6.2 6.2 0 0 1 12.4 0V19z" /><path d="M16 4.5a3.1 3.1 0 0 1 0 6M18 13a5 5 0 0 1 3.2 4.7V19h-3" /></svg>
        </button>

        <nav className="abas-pacientes" aria-label="Pacientes abertos">
          {pacientes.filter(p => abasAbertas.includes(p.id)).map(p => (
            <div key={p.id} className={`aba-paciente-wrapper ${p.id === pacienteAtivoId ? 'ativa' : ''}`}>
              <button className={`aba-paciente ${p.id === pacienteAtivoId ? 'ativa' : ''}`} onClick={() => selecionarPaciente(p.id)} title={`Abrir exames de ${p.nome}`}>
                <UserIcon /><span>{p.nome}</span>
              </button>
              <button className="fechar-aba-paciente" onClick={() => fecharAbaPaciente(p.id)} title={`Fechar aba de ${p.nome}`} aria-label={`Fechar aba de ${p.nome}`}>×</button>
            </div>
          ))}
        </nav>

        <div className="acoes-topbar">
          <button className="configuracoes" title="Configurações" aria-label="Abrir configurações" onClick={() => { setConfigAberta(v => !v); setHistoricoAberto(false) }}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8.2a3.8 3.8 0 1 0 0 7.6 3.8 3.8 0 0 0 0-7.6Z" /><path d="m19.4 13.5 1.2.9-1.6 2.8-1.4-.6a7.9 7.9 0 0 1-1.6.9l-.2 1.5h-3.3l-.3-1.5a7.9 7.9 0 0 1-1.6-.9l-1.4.6-1.6-2.8 1.2-.9a7.4 7.4 0 0 1 0-1.8l-1.2-.9 1.6-2.8 1.4.6a7.9 7.9 0 0 1 1.6-.9l.3-1.5h3.3l.2 1.5a7.9 7.9 0 0 1 1.6.9l1.4-.6 1.6 2.8-1.2.9a7.4 7.4 0 0 1 0 1.8Z" transform="translate(-1 -1) scale(1.08)" /></svg>
          </button>
        </div>

        {historicoAberto && <section className="popover-topo historico-popover">
          <div className="popover-cabecalho"><div><h2>Pacientes</h2><p>Selecione um paciente para abrir seus exames.</p></div><button className="fechar-popover" onClick={() => setHistoricoAberto(false)} aria-label="Fechar">×</button></div>
          <input className="busca-pacientes" value={busca} onChange={e => setBusca(e.target.value)} placeholder="Buscar paciente..." />
          <div className="lista-pacientes">
            {pacientesFiltrados.map(p => <button key={p.id} className={`item-paciente ${p.id === pacienteAtivoId ? 'ativo' : ''}`} onClick={() => selecionarPaciente(p.id)}>
              <span className="avatar-paciente"><UserIcon /></span><span className="dados-lista-paciente"><strong>{p.nome}</strong><small>{p.exames.length} exame(s)</small></span><span className="seta-lista">›</span>
            </button>)}
            {pacientesFiltrados.length === 0 && <p className="sem-resultados">Nenhum paciente encontrado.</p>}
          </div>
          <button className="botao-novo-paciente" onClick={() => setMostrarNovoPaciente(v => !v)}>+ Novo paciente</button>
          {mostrarNovoPaciente && <form className="form-novo-paciente" onSubmit={criarPaciente}>
            <label>Nome completo<input autoFocus value={nomeNovoPaciente} onChange={e => setNomeNovoPaciente(e.target.value)} required placeholder="Nome do paciente" /></label>
            <label>Peso (kg)<input type="number" min="0" step="0.1" value={pesoNovoPaciente} onChange={e => setPesoNovoPaciente(e.target.value)} placeholder="Ex.: 70" /></label>
            <label>Observações<textarea value={observacoesNovoPaciente} onChange={e => setObservacoesNovoPaciente(e.target.value)} placeholder="Informações adicionais" /></label>
            <button className="botao-laranja" type="submit">Criar paciente</button>
          </form>}
        </section>}

        {configAberta && <section className="popover-topo config-popover">
          <div className="popover-cabecalho"><div><h2>Configurações</h2><p>Preferências da interface</p></div><button className="fechar-popover" onClick={() => setConfigAberta(false)} aria-label="Fechar">×</button></div>
          <div className="config-item"><span>Tema</span><strong>Escuro</strong></div>
          <div className="config-item"><span>Dataset de referência</span><strong>LUNA16</strong></div>
          <div className="config-item"><span>API</span><strong>{API_URL}</strong></div>
          <div className="config-item"><span>Conexão</span><strong>{estadoApi.conectada ? 'Conectada' : 'Desconectada'}</strong></div>
          <div className="config-item"><span>Origem dos resultados</span><strong>{estadoApi.modo ? NOMES_MODO[estadoApi.modo] ?? estadoApi.modo : '—'}</strong></div>
          <p className="config-aviso">Protótipo acadêmico. Não é um dispositivo médico e não deve ser usado para diagnóstico.</p>
        </section>}
      </header>

      <div className="layout">
        <aside className="sidebar">
          <section className="painel paciente">
            <h2>Informações do paciente</h2>
            <label>Nome:<input value={pacienteAtivo.nome} readOnly /></label>
            <label>Peso (kg):<input type="number" min="0" step="0.1" value={pacienteAtivo.peso} onChange={e => atualizarPacienteAtual('peso', e.target.value)} placeholder="Peso do paciente" /></label>
            <label>Observações:<textarea value={pacienteAtivo.observacoes} onChange={e => atualizarPacienteAtual('observacoes', e.target.value)} placeholder="Informações adicionais" /></label>
          </section>

          <section className="painel resultados">
            <h2>Resultado da<br />segmentação:</h2>
            {exameAtivo.resultado ? <>
              <table className="tabela-resultados">
                <thead><tr><th>Método</th><th>Dice</th><th>IoU</th><th>{porEnvio ? 'Área' : 'Volume'}</th><th>Tempo</th></tr></thead>
                <tbody>
                  {METODOS.map(m => {
                    const r = exameAtivo.resultado.metodos[m.id].metricas
                    return <tr key={m.id}>
                      <td><span className="ponto-cor" style={{ background: `rgb(${m.cor.join(',')})` }} />{m.nome}</td>
                      <td>{formatar(r.dice)}</td><td>{formatar(r.iou)}</td>
                      <td>{porEnvio ? `${formatar(r.area_pulmonar_cm2, 1)} cm²` : `${formatar(r.volume_pulmonar_ml / 1000, 2)} L`}</td>
                      <td>{formatar(r.tempo_ms / 1000, 1)} s</td>
                    </tr>
                  })}
                </tbody>
              </table>
              {porEnvio ? <>
                <p><span>Arquivo analisado:</span><strong>{exameAtivo.resultado.arquivo}</strong></p>
                <small className="nota-resultados">{exameAtivo.resultado.gabarito
                  ? 'Dice e IoU desta fatia, contra a máscara de referência do LUNA16 (a fatia enviada é do Teste A).'
                  : 'Imagem sem gabarito: não há Dice nem IoU. A tabela mostra a área de pulmão encontrada por cada método.'}</small>
              </> : <>
                <p><span>Fatias do exame:</span><strong>{examesApi.find(e => e.id === exameAtivo.exameApiId)?.num_fatias ?? '—'}</strong></p>
                <small className="nota-resultados">Dice e IoU do exame inteiro (3D), contra a máscara de referência do LUNA16.</small>
              </>}
            </> : <>
              <p><span>Dice (exame inteiro):</span><strong>—</strong></p>
              <p><span>Volume pulmonar:</span><strong>—</strong></p>
              <p><span>Fatias do exame:</span><strong>—</strong></p>
              <p className="tempo"><span>Tempo:</span><strong>— segundos</strong></p>
            </>}
            <button className="botao-laranja" onClick={salvarResultado}>Salvar resultado</button>
            <small>{estadoApi.modo ? NOMES_MODO[estadoApi.modo] ?? estadoApi.modo : (estadoApi.erro ?? 'Conectando à API...')}</small>
          </section>
        </aside>

        <main className="conteudo">
          <section className="visualizador painel">
            <div className="titulo-visualizador">
              <div><span className="nome-paciente-visualizador">{pacienteAtivo.nome}</span><span className="separador-titulo"> / </span><span>{exameAtivo.nome}</span></div>
              <span className="status">{exameAtivo.status}</span>
            </div>
            <div className="imagem-tomografia">
              {exameAtivo.resultado ? <div className="grade-metodos">
                {METODOS.map(m => <figure key={m.id} className="painel-metodo">
                  <Sobreposicao fatiaUrl={exameAtivo.resultado.fatia.url} mascaraUrl={exameAtivo.resultado.metodos[m.id].mascaraUrl} cor={m.cor} titulo={`Máscara do ${m.nome}`} />
                  <figcaption><span className="ponto-cor" style={{ background: `rgb(${m.cor.join(',')})` }} />{m.nome} · {exameAtivo.resultado.metodos[m.id].metricas.dice === null
                    ? `${formatar(exameAtivo.resultado.metodos[m.id].metricas.area_pulmonar_cm2, 1)} cm²`
                    : `Dice ${formatar(exameAtivo.resultado.metodos[m.id].metricas.dice)}`}</figcaption>
                </figure>)}
                {porEnvio && exameAtivo.resultado.avisos.length > 0 && <ul className="avisos-analise">
                  {exameAtivo.resultado.avisos.map(a => <li key={a}>{a}</li>)}
                </ul>}
              </div> : exameAtivo.exameApiId ? <div className="arquivo-carregado"><span className="simbolo-tomografia">▦</span><h3>Tomografia do servidor selecionada</h3><p>{examesApi.find(e => e.id === exameAtivo.exameApiId)?.nome ?? exameAtivo.exameApiId}</p><small>Clique em “Iniciar segmentação”.</small></div> : exameAtivo.arquivo ?<div className="arquivo-carregado"><span className="simbolo-tomografia">▦</span><h3>Arquivo selecionado</h3><p>{exameAtivo.arquivo.name}</p><small>Clique em “Iniciar segmentação” para a API analisar a imagem com os três métodos.</small></div> : <div className="mensagem-vazia"><span className="simbolo-tomografia">⌕</span><h3>Aguardando processamento</h3><p>Carregue uma tomografia para este exame</p></div>}
            </div>
            <div className="rodape-visualizador"><span>Dataset: LUNA16</span><span>{exameAtivo.data}</span><span>Fatia: {exameAtivo.fatia}</span>{porEnvio ? <span className="modo-api modo-modelo_real">{NOMES_MODO.modelo_real}</span>
                : estadoApi.modo && <span className={`modo-api modo-${estadoApi.modo}`}>{NOMES_MODO[estadoApi.modo] ?? estadoApi.modo}</span>}</div>
          </section>

          <div className="area-inferior">
            <div className="coluna-inferior">
              <section className="painel informacoes-arquivo">
                <p><strong>Paciente:</strong> {pacienteAtivo.nome}</p><p><strong>Exame:</strong> {exameAtivo.nome}</p><p><strong>Data:</strong> {exameAtivo.data}</p><p><strong>Formato:</strong> {exameAtivo.arquivo?.name ?? (exameAtivo.exameApiId ? '.mhd / .raw (servidor)' : '.png / .jpg / .dcm')}</p><p><strong>Status:</strong> {exameAtivo.status}</p>
              </section>
              <div className="controles-fatias">
                <button className="seta" onClick={() => mudarExame(-1)} disabled={indiceExame === 0} title="Exame anterior deste paciente" aria-label="Exame anterior">◀</button>
                <div className="controle-exame-centro"><button className="botao-adicionar" title="Criar novo exame para este paciente" onClick={criarNovoExame}>+</button><small>{indiceExame + 1} de {pacienteAtivo.exames.length} exames</small></div>
                <button className="seta" onClick={() => mudarExame(1)} disabled={indiceExame === pacienteAtivo.exames.length - 1} title="Próximo exame deste paciente" aria-label="Próximo exame">▶</button>
              </div>
            </div>

            <section className="painel upload">
              <label className="escolha-servidor">Tomografia do servidor (LUNA16)
                <select value={exameAtivo.exameApiId ?? ''} onChange={e => escolherExameApi(e.target.value)} disabled={!estadoApi.conectada}>
                  <option value="">{estadoApi.conectada ? 'Escolha um exame...' : (estadoApi.erro ?? 'Conectando à API...')}</option>
                  {examesApi.map(e => <option key={e.id} value={e.id}>{e.nome}</option>)}
                </select>
              </label>
              <label htmlFor="arquivo" className="area-upload" onDragOver={e => e.preventDefault()} onDrop={soltarArquivo}>
                <span className="mais-upload">+</span><strong>{exameAtivo.arquivo ? 'Arquivo selecionado' : 'Arraste a tomografia para esta área'}</strong><span>ou</span><small>{exameAtivo.arquivo ? exameAtivo.arquivo.name : 'Clique aqui para procurar o arquivo'}</small>
              </label>
              <input ref={inputArquivoRef} id="arquivo" type="file" accept={FORMATOS_ENVIO} onChange={selecionarArquivo} hidden />
              <button className="botao-laranja botao-upload" onClick={() => inputArquivoRef.current?.click()}>⇧ Fazer Upload</button>
              <button className="botao-processar" disabled={(!exameAtivo.exameApiId && !exameAtivo.arquivo) || segmentando} onClick={iniciarSegmentacao}>{segmentando ? 'Segmentando...' : 'Iniciar segmentação'}</button>
            </section>
          </div>

          {mensagem && <div className="mensagem-feedback" role="status"><span>{mensagem}</span><button onClick={() => setMensagem('')} aria-label="Fechar mensagem">×</button></div>}
        </main>
      </div>
    </div>
  )
}

export default App
