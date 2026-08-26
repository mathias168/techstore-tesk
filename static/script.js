/* ==========================================================
   1. MÁSCARAS DE FORMATAÇÃO (Telefone e CEP)
   ========================================================== */
document.addEventListener("DOMContentLoaded", () => {
    const inputTelefone = document.querySelector("input[name='telefone']");
    const inputCep = document.querySelector("input[name='cep']");

    if (inputTelefone) {
        inputTelefone.addEventListener("input", (e) => {
            let valor = e.target.value.replace(/\D/g, "");
            if (valor.length > 11) valor = valor.slice(0, 11);
            if (valor.length > 6) {
                valor = `(${valor.slice(0, 2)}) ${valor.slice(2, 7)}-${valor.slice(7)}`;
            } else if (valor.length > 2) {
                valor = `(${valor.slice(0, 2)}) ${valor.slice(2)}`;
            } else if (valor.length > 0) {
                valor = `(${valor}`;
            }
            e.target.value = valor;
        });
    }

    if (inputCep) {
        inputCep.addEventListener("input", (e) => {
            let valor = e.target.value.replace(/\D/g, "");
            if (valor.length > 8) valor = valor.slice(0, 8);
            if (valor.length > 5) {
                valor = `${valor.slice(0, 5)}-${valor.slice(5)}`;
            }
            e.target.value = valor;
        });
    }

    /* ==========================================================
       2. VALIDAÇÃO DO FORMULÁRIO DE CHECKOUT
       ========================================================== */
    const formDetalhes = document.querySelector("form[action*='comprar-formulario']");
    if (formDetalhes) {
        formDetalhes.addEventListener("submit", (e) => {
            const tel = inputTelefone ? inputTelefone.value.replace(/\D/g, "") : "";
            const cep = inputCep ? inputCep.value.replace(/\D/g, "") : "";

            if (tel.length < 10) {
                alert("Por favor, digite um telefone/WhatsApp válido com DDD.");
                e.preventDefault();
                return;
            }

            if (cep.length !== 8) {
                alert("O CEP deve conter exatamente 8 dígitos.");
                e.preventDefault();
                return;
            }
        });
    }

    /* ==========================================================
       3. BUSCA DINÂMICA EM TEMPO REAL (Auto-complete)
       ========================================================== */
    const inputBusca = document.querySelector(".input-pesquisa");
    if (inputBusca) {
        inputBusca.addEventListener("input", (e) => {
            const termo = e.target.value.toLowerCase().trim();
            const cards = document.querySelectorAll(".card-produto");

            cards.forEach(card => {
                const nomeProduto = card.querySelector(".produto-nome").textContent.toLowerCase();
                const categoriaProduto = card.querySelector(".produto-codigo").textContent.toLowerCase();

                if (nomeProduto.includes(termo) || categoriaProduto.includes(termo)) {
                    card.style.display = "flex";
                } else {
                    card.style.display = "none";
                }
            });
        });
    }
});

/* ==========================================================
   4. ALERTA FLUTUANTE (TOAST) AO ADICIONAR AO CARRINHO
   ========================================================== */
function adicionarComAjax(event, url) {
    event.preventDefault(); // Impede o recarregamento da página

    fetch(url, {
        method: "POST",
    })
    .then(response => {
        if (response.ok) {
            mostrarToast("Produto adicionado ao carrinho com sucesso!");
            
            // Atualiza o contador do carrinho no topo da página dinamicamente
            atualizarContadorCarrinho();
        }
    })
    .catch(error => console.error("Erro ao adicionar:", error));
}

function mostrarToast(mensagem) {
    // Cria o elemento do Toast se não existir
    let toast = document.getElementById("toast-alerta");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "toast-alerta";
        document.body.appendChild(toast);
    }

    toast.textContent = mensagem;
    toast.className = "toast-visivel";

    // Some após 3 segundos
    setTimeout(() => {
        toast.className = "";
    }, 3000);
}

function atualizarContadorCarrinho() {
    fetch("/api/qtd-carrinho")
    .then(res => res.json())
    .then(data => {
        const linkCarrinho = document.querySelector(".nav-btn-carrinho");
        if (linkCarrinho) {
            linkCarrinho.textContent = `🛒 Carrinho (${data.total})`;
        }
    });
}