import { useRef, useState } from 'react'
import './App.css'

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

  const pacienteAtivo = pacientes.find(p => p.id === pacienteAtivoId) ?? pacientes.find(p => abasAbertas.includes(p.id)) ?? null
  const exameAtivo = pacienteAtivo ? (pacienteAtivo.exames.find(e => e.id === pacienteAtivo.exameAtivoId) ?? pacienteAtivo.exames[0]) : null
  const indiceExame = pacienteAtivo && exameAtivo ? pacienteAtivo.exames.findIndex(e => e.id === exameAtivo.id) : -1
  const pacientesFiltrados = pacientes.filter(p => p.nome.toLowerCase().includes(busca.toLowerCase()))

  function atualizarExameAtual(mudancas) {
    setPacientes(atuais => atuais.map(p => p.id !== pacienteAtivoId ? p : {
      ...p,
      exames: p.exames.map(e => e.id === exameAtivo.id ? { ...e, ...mudancas } : e),
    }))
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
    atualizarExameAtual({ arquivo: selecionado, status: 'Arquivo selecionado', fatia: 1 })
    setMensagem(`Arquivo associado a ${pacienteAtivo.nome} — ${exameAtivo.nome}.`)
    event.target.value = ''
  }

  function soltarArquivo(event) {
    event.preventDefault()
    const dropped = event.dataTransfer.files?.[0]
    if (!dropped) return
    atualizarExameAtual({ arquivo: dropped, status: 'Arquivo selecionado', fatia: 1 })
    setMensagem(`Arquivo associado a ${pacienteAtivo.nome} — ${exameAtivo.nome}.`)
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
        status: exameAtivo.status, fatia: exameAtivo.fatia, resultadosSegmentacao: null,
      },
      aviso: 'Demonstração: resultados reais dependem da integração com o backend.',
    }
    const blob = new Blob([JSON.stringify(resultado, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${pacienteAtivo.nome.replace(/\s+/g, '_')}_${exameAtivo.nome}.json`
    link.click()
    URL.revokeObjectURL(url)
    setMensagem('Resumo demonstrativo salvo em JSON.')
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
          <p className="config-aviso">As configurações clínicas e de processamento serão definidas na integração com o backend.</p>
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
            <p><span>Área segmentada:</span><strong>— cm²</strong></p>
            <p><span>Parênquima:</span><strong>—</strong></p>
            <p><span>Fatias analisadas:</span><strong>—</strong></p>
            <p className="tempo"><span>Tempo:</span><strong>— segundos</strong></p>
            <button className="botao-laranja" onClick={salvarResultado}>Salvar resultado</button>
            <small>Resultados reais aparecerão após a integração do modelo.</small>
          </section>
        </aside>

        <main className="conteudo">
          <section className="visualizador painel">
            <div className="titulo-visualizador">
              <div><span className="nome-paciente-visualizador">{pacienteAtivo.nome}</span><span className="separador-titulo"> / </span><span>{exameAtivo.nome}</span></div>
              <span className="status">{exameAtivo.status}</span>
            </div>
            <div className="imagem-tomografia">
              {exameAtivo.arquivo ? <div className="arquivo-carregado"><span className="simbolo-tomografia">▦</span><h3>Arquivo selecionado</h3><p>{exameAtivo.arquivo.name}</p><small>Visualização médica será conectada ao backend.</small></div> : <div className="mensagem-vazia"><span className="simbolo-tomografia">⌕</span><h3>Aguardando processamento</h3><p>Carregue uma tomografia para este exame</p></div>}
            </div>
            <div className="rodape-visualizador"><span>Dataset: LUNA16</span><span>{exameAtivo.data}</span><span>Fatia: {exameAtivo.fatia}</span></div>
          </section>

          <div className="area-inferior">
            <div className="coluna-inferior">
              <section className="painel informacoes-arquivo">
                <p><strong>Paciente:</strong> {pacienteAtivo.nome}</p><p><strong>Exame:</strong> {exameAtivo.nome}</p><p><strong>Data:</strong> {exameAtivo.data}</p><p><strong>Formato:</strong> {exameAtivo.arquivo?.name ?? '.mhd / .raw'}</p><p><strong>Status:</strong> {exameAtivo.status}</p>
              </section>
              <div className="controles-fatias">
                <button className="seta" onClick={() => mudarExame(-1)} disabled={indiceExame === 0} title="Exame anterior deste paciente" aria-label="Exame anterior">◀</button>
                <div className="controle-exame-centro"><button className="botao-adicionar" title="Criar novo exame para este paciente" onClick={criarNovoExame}>+</button><small>{indiceExame + 1} de {pacienteAtivo.exames.length} exames</small></div>
                <button className="seta" onClick={() => mudarExame(1)} disabled={indiceExame === pacienteAtivo.exames.length - 1} title="Próximo exame deste paciente" aria-label="Próximo exame">▶</button>
              </div>
            </div>

            <section className="painel upload">
              <label htmlFor="arquivo" className="area-upload" onDragOver={e => e.preventDefault()} onDrop={soltarArquivo}>
                <span className="mais-upload">+</span><strong>{exameAtivo.arquivo ? 'Arquivo selecionado' : 'Arraste a tomografia para esta área'}</strong><span>ou</span><small>{exameAtivo.arquivo ? exameAtivo.arquivo.name : 'Clique aqui para procurar o arquivo'}</small>
              </label>
              <input ref={inputArquivoRef} id="arquivo" type="file" accept=".mhd,.raw,.nii,.nii.gz,.dcm,.png,.jpg,.jpeg" onChange={selecionarArquivo} hidden />
              <button className="botao-laranja botao-upload" onClick={() => inputArquivoRef.current?.click()}>⇧ Fazer Upload</button>
              <button className="botao-processar" disabled={!exameAtivo.arquivo} onClick={() => { atualizarExameAtual({ status: 'Pronto para integração com backend' }); setMensagem('A interface ainda não executa a segmentação real.') }}>Iniciar segmentação</button>
            </section>
          </div>

          {mensagem && <div className="mensagem-feedback" role="status"><span>{mensagem}</span><button onClick={() => setMensagem('')} aria-label="Fechar mensagem">×</button></div>}
        </main>
      </div>
    </div>
  )
}

export default App
