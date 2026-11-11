const API = "/api";

async function request(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  if (!response.ok) {
    let detail = `Erro HTTP ${response.status}`;
    try {
      const data = await response.json();
      detail = JSON.stringify(data);
    } catch {}
    throw new Error(detail);
  }

  return response.status === 204 ? null : response.json();
}

let produtos = [];

function csrfToken() {
  const cookie = document.cookie
    .split("; ")
    .find(row => row.startsWith("csrftoken="));
  return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
}

function statusProduto(produto) {
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);

  if (produto.quantidade_estoque === 0) {
    return ["Sem estoque", "status-vencido"];
  }

  if (produto.quantidade_estoque <= produto.estoque_minimo) {
    return ["Estoque baixo", "status-baixo"];
  }

  if (produto.data_validade) {
    const validade = new Date(produto.data_validade + "T00:00:00");
    const dias = Math.ceil((validade - hoje) / 86400000);

    if (dias < 0) {
      return ["Vencido", "status-vencido"];
    }

    if (dias <= 30) {
      return ["Próximo do vencimento", "status-baixo"];
    }
  }

  return ["Normal", "status-normal"];
}

function renderProdutos() {
  const busca = document.querySelector("#busca").value
    .trim()
    .toLowerCase();

  const tbody = document.querySelector("#tabelaProdutos");
  tbody.innerHTML = "";

  produtos
    .filter(p => p.nome.toLowerCase().includes(busca))
    .forEach(p => {
      const [status, classe] = statusProduto(p);

      tbody.insertAdjacentHTML(
        "beforeend",
        `<tr>
          <td>${p.nome}</td>
          <td>${p.categoria_nome}</td>
          <td>${p.quantidade_estoque}</td>
          <td>${p.estoque_minimo}</td>
          <td>${p.data_validade || "-"}</td>
          <td class="${classe}">${status}</td>
        </tr>`
      );
    });
}

function renderDashboard() {
  document.querySelector("#totalProdutos").textContent = produtos.length;

  document.querySelector("#estoqueBaixo").textContent =
    produtos.filter(p =>
      p.quantidade_estoque > 0 &&
      p.quantidade_estoque <= p.estoque_minimo
    ).length;

  document.querySelector("#semEstoque").textContent =
    produtos.filter(p => p.quantidade_estoque === 0).length;

  document.querySelector("#vencidos").textContent =
    produtos.filter(p => statusProduto(p)[0] === "Vencido").length;
}

function renderProdutosParaMovimentacao() {
  const select = document.querySelector("#movProduto");

  select.innerHTML = produtos
    .map(p => `<option value="${p.id}">${p.nome}</option>`)
    .join("");
}

function renderValidade() {
  const lista = document.querySelector("#listaValidade");

  const alertas = produtos.filter(p => {
    const status = statusProduto(p)[0];
    return status === "Próximo do vencimento" || status === "Vencido";
  });

  if (!alertas.length) {
    lista.innerHTML = "<p>Nenhum produto em alerta de validade.</p>";
    return;
  }

  lista.innerHTML = alertas.map(p => {
    const [status, classe] = statusProduto(p);
    return `<p class="${classe}">
      <strong>${p.nome}</strong> —
      validade: ${p.data_validade} —
      ${status}
    </p>`;
  }).join("");
}

async function carregarProdutos() {
  produtos = await request(`${API}/produtos/`);
  renderProdutos();
  renderDashboard();
  renderProdutosParaMovimentacao();
  renderValidade();
}

async function buscarOuCriarCategoria(nome) {
  const categorias = await request(`${API}/categorias/`);
  const existente = categorias.find(
    c => c.nome.toLowerCase() === nome.toLowerCase()
  );

  if (existente) return existente;

  return request(`${API}/categorias/`, {
    method: "POST",
    headers: {"X-CSRFToken": csrfToken()},
    body: JSON.stringify({nome})
  });
}

document.querySelector("#produtoForm").addEventListener("submit", async event => {
  event.preventDefault();

  try {
    const categoria = await buscarOuCriarCategoria(
      document.querySelector("#categoria").value.trim()
    );

    await request(`${API}/produtos/`, {
      method: "POST",
      headers: {"X-CSRFToken": csrfToken()},
      body: JSON.stringify({
        nome: document.querySelector("#nome").value.trim(),
        categoria: categoria.id,
        preco: document.querySelector("#preco").value,
        quantidade_estoque: Number(
          document.querySelector("#quantidade").value
        ),
        estoque_minimo: Number(
          document.querySelector("#minimo").value
        ),
        data_validade:
          document.querySelector("#validade").value || null,
        ativo: true
      })
    });

    event.target.reset();
    await carregarProdutos();
    alert("Produto cadastrado com sucesso.");
  } catch (error) {
    console.error(error);
    alert("Não foi possível cadastrar o produto.");
  }
});

document.querySelector("#movForm").addEventListener("submit", async event => {
  event.preventDefault();

  try {
    await request(`${API}/movimentacoes/`, {
      method: "POST",
      headers: {"X-CSRFToken": csrfToken()},
      body: JSON.stringify({
        produto: Number(
          document.querySelector("#movProduto").value
        ),
        tipo: document.querySelector("#movTipo").value,
        quantidade: Number(
          document.querySelector("#movQuantidade").value
        ),
        observacao:
          document.querySelector("#movObservacao").value.trim()
      })
    });

    document.querySelector("#mensagem").textContent =
      "Movimentação registrada com sucesso.";

    event.target.reset();
    await carregarProdutos();
  } catch (error) {
    console.error(error);
    document.querySelector("#mensagem").textContent =
      "Não foi possível registrar a movimentação. Verifique o estoque.";
  }
});

document.querySelector("#busca").addEventListener(
  "input",
  renderProdutos
);

carregarProdutos().catch(error => {
  console.error(error);
});
