function doGet(e) {
    try {
        atualizarBaseLookerStudio();

        return ContentService.createTextOutput(
            JSON.stringify({ "status": "sucesso", "mensagem": "A base Looker Studio foi atualizada com sucesso!" })
        ).setMimeType(ContentService.MimeType.JSON);

    } catch (error) {
        return ContentService.createTextOutput(
            JSON.stringify({ "status": "erro", "mensagem": error.message, "stack": error.stack })
        ).setMimeType(ContentService.MimeType.JSON);
    }
}

function atualizarBaseLookerStudio() {
    var ss = SpreadsheetApp.getActiveSpreadsheet();

    var sheetBrutos = ss.getSheetByName('dados_brutos');
    var sheetPosts = ss.getSheetByName('dados_posts');
    var sheetLooker = ss.getSheetByName('base_looker_studio_posts');

    var dataBrutos = sheetBrutos.getDataRange().getValues();
    var dataPosts = sheetPosts.getDataRange().getValues();

    var mapPosts = {};

    for (var i = 1; i < dataPosts.length; i++) {
        var idPost = dataPosts[i][0];
        if (idPost) {
            mapPosts[idPost] = {
                id_myside: dataPosts[i][2],
                titulo_referencia: dataPosts[i][3],
                formato: dataPosts[i][4],
                tipo_midia: dataPosts[i][5],
                categoria_conteudo: dataPosts[i][6],
                linha_editorial: dataPosts[i][7]
            };
        }
    }

    var resultData = [];
    var headersBrutos = dataBrutos[0];

    var novoCabecalho = [
        "id_interno", "data_publicacao", "cidade", "perfil", "rede_social",
        "curtidas", "comentarios", "salvos", "compartilhamentos", "taxa_engajamento", "alcance", "taxa_alcance", "titulo_referencia", "formato", "tipo_midia", "categoria_conteudo", "linha_editorial"
    ];
    resultData.push(novoCabecalho);

    // SOLUÇÃO: Buscando os índices dinamicamente ao invés de fixar números
    // Normaliza os cabeçalhos para evitar problemas com espaços ou maiúsculas
    var headersNormalized = headersBrutos.map(function (h) {
        return h ? String(h).trim().toLowerCase() : "";
    });

    var idxIdInterno = headersNormalized.indexOf("id_interno");
    var idxData = headersNormalized.indexOf("data_publicacao");
    var idxCidade = headersNormalized.indexOf("cidade");
    var idxPerfil = headersNormalized.indexOf("perfil");
    var idxRede = headersNormalized.indexOf("rede_social");

    var idxLikes = headersNormalized.indexOf("curtidas");
    var idxComents = headersNormalized.indexOf("comentarios");
    var idxSalvos = headersNormalized.indexOf("salvos");
    var idxCompart = headersNormalized.indexOf("compartilhamentos");
    var idxTaxaEngajamento = headersNormalized.indexOf("taxa_engajamento");
    var idxAlcance = headersNormalized.indexOf("alcance");
    var idxTaxaAlcance = headersNormalized.indexOf("taxa_alcance");


    for (var j = 1; j < dataBrutos.length; j++) {
        var rowB = dataBrutos[j];
        var idInterno = idxIdInterno !== -1 ? rowB[idxIdInterno] : "";

        var infoPost = mapPosts[idInterno];

        var postRecord = infoPost ? infoPost : {
            id_myside: "", titulo_referencia: "", formato: "",
            tipo_midia: "", categoria_conteudo: "", linha_editorial: ""
        };

        // NOVO: Filtro para ignorar posts de teste
        if (postRecord.titulo_referencia && String(postRecord.titulo_referencia).trim().toLowerCase() === "teste") {
            continue;
        }

        // Pega o valor se a coluna existir, senão deixa em branco
        var valData = idxData !== -1 ? rowB[idxData] : "";
        var valCidade = idxCidade !== -1 ? rowB[idxCidade] : "";
        var valPerfil = idxPerfil !== -1 ? rowB[idxPerfil] : "";
        var valRede = idxRede !== -1 ? rowB[idxRede] : "";
        var valLikes = idxLikes !== -1 ? rowB[idxLikes] : "";
        var valComents = idxComents !== -1 ? rowB[idxComents] : "";
        var valSalvos = idxSalvos !== -1 ? rowB[idxSalvos] : "";
        var valCompart = idxCompart !== -1 ? rowB[idxCompart] : "";
        var valTaxaEngajamento = idxTaxaEngajamento !== -1 ? rowB[idxTaxaEngajamento] : "";
        var valAlcance = idxAlcance !== -1 ? rowB[idxAlcance] : "";
        var valTaxaAlcance = idxTaxaAlcance !== -1 ? rowB[idxTaxaAlcance] : "";


        resultData.push([
            idInterno,
            valData,
            valCidade,
            valPerfil,
            valRede,
            valLikes,
            valComents,
            valSalvos,
            valCompart,
            valTaxaEngajamento,
            valAlcance,
            valTaxaAlcance,
            postRecord.titulo_referencia,
            postRecord.formato,
            postRecord.tipo_midia,
            postRecord.categoria_conteudo,
            postRecord.linha_editorial
        ]);
    }

    sheetLooker.clearContents();
    sheetLooker.getRange(1, 1, resultData.length, resultData[0].length).setValues(resultData);
}
