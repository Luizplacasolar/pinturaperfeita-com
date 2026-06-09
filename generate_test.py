"""
PINTURA PERFEITA — Script de teste de geração de PDF
Execute: python3 generate_test.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from pdf_generator import generate_from_dict

# ─── Dados de exemplo (espelha o que vem do frontend) ────────
TEST_ESTIMATE = {
    "code": "PP-A1B2C3",
    "created_at": "2026-05-03",
    "validity_days": 30,
    "warranty": "1 ano",
    "payment_terms": "50% entrada + 50% conclusão",
    "observations": "Acesso ao imóvel disponível de segunda a sábado, das 7h às 17h. Necessário deixar janelas abertas após pintura por 24h para ventilação.",
    "property_address": "Rua das Flores, 123 — Jardim Paulista, São Paulo/SP",
    "ai_description": (
        "A proposta contempla a pintura completa de residência unifamiliar de médio padrão, "
        "incluindo preparação adequada das superfícies com massa corrida e selador de qualidade. "
        "Serão utilizados produtos Suvinil linha Premium, com garantia de acabamento superior "
        "e durabilidade mínima de 5 anos. A equipe especializada seguirá todas as normas técnicas "
        "da ABNT para execução de pinturas prediais, garantindo resultado profissional e duradouro."
    ),

    # Dados da empresa
    "company": {
        "name": "Pintura Perfeita Pro",
        "cnpj": "12.345.678/0001-90",
        "phone": "(11) 98765-4321",
        "email": "contato@pinturaperfeita.com",
        "website": "pinturaperfeita.com",
        "address": "Rua Augusta, 500 — São Paulo, SP",
        "slogan": "Soluções Profissionais em Pintura Predial",
    },

    # Dados do cliente
    "client": {
        "name": "Ricardo Mendonça",
        "phone": "(11) 98765-0001",
        "email": "rm@empresa.com.br",
        "city": "São Paulo",
        "document": "123.456.789-00",
    },

    # Formulário (inputs do wizard)
    "form": {
        "propertyType":    "casa_residencial",
        "totalArea":       180,
        "wallHeight":      2.8,
        "numRooms":        6,
        "wallCondition":   "boa",
        "hasInternal":     True,
        "hasExternal":     False,
        "hasCeiling":      True,
        "hasMassaCorrida": True,
        "hasTexture":      False,
        "hasFacade":       False,
        "hasWalls":        False,
        "paintType":       "premium",
        "numCoats":        2,
        "workerDailyRate": 320,
        "helperDailyRate": 190,
        "profitMargin":    32,
    },

    # Valores calculados
    "calc": {
        "paintLiters":    26,
        "paintCost":      1144.00,
        "massaKg":        175,
        "massaCost":      787.50,
        "seladorL":       8,
        "seladorCost":    176.00,
        "rolos":          3,
        "miscCost":       389.00,
        "materialsCost":  2496.50,
        "workDays":       8,
        "numWorkers":     2,
        "numHelpers":     1,
        "laborCost":      6640.00,
        "subtotal":       9136.50,
        "profit":         2923.68,
        "total":          12060.18,
        "pricePerM2":     67.00,
        "paintArea":      228.00,
    },

    # Itens opcionais detalhados
    "items": [
        {"name": "Tinta Acrílica Premium Coral", "qty": 26, "unit": "litros",   "price": 44.00,  "total": 1144.00},
        {"name": "Massa Corrida PVA Suvinil",     "qty": 175,"unit": "kg",      "price": 4.50,   "total": 787.50},
        {"name": "Selador Acrílico",              "qty": 8,  "unit": "litros",  "price": 22.00,  "total": 176.00},
        {"name": "Rolos de Lã 23cm",              "qty": 3,  "unit": "unid.",   "price": 18.00,  "total": 54.00},
        {"name": "Fitas e Plásticos",             "qty": 1,  "unit": "kit",     "price": 335.00, "total": 335.00},
    ],
}

if __name__ == "__main__":
    out = "/home/claude/pdf-generator/proposta_teste.pdf"
    print("🎨 Gerando proposta PDF...")
    result = generate_from_dict(TEST_ESTIMATE, out)
    size = os.path.getsize(result) / 1024
    print(f"✅ PDF gerado: {result}")
    print(f"   Tamanho: {size:.1f}KB")
    print(f"   Proposta: {TEST_ESTIMATE['code']} — {TEST_ESTIMATE['client']['name']}")
    print(f"   Total: R$ {TEST_ESTIMATE['calc']['total']:,.2f}")
