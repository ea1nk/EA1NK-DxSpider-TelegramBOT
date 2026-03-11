STRINGS = {
    'es': {
        'start': "<b>¡73, {name}!</b> 🎙️\nBienvenido a tu bot DX con soporte RBN.",
        'help': (
            "<b>Guía de Comandos:</b>\n\n"
            "• /setfilter [DX] [Banda] [Modo] - Crear alerta e historial.\n"
            "• /last [DX] - Ver últimos 10 spots (30 min).\n"
            "• /rbn [on|off] - Activar/Desactivar spots de Skimmers/RBN.\n"
            "• /myfilters - Ver tus alertas activas.\n"
            "• /delfilter [ID] - Borrar una alerta.\n\n"
            "ℹ️ <i>Nota: Se filtran duplicados automáticamente cada 10 min.</i>"
        ),
        'rbn_status': "✅ Spots de RBN ahora: <b>{status}</b>",
        'spot': "🎯 <b>SPOT</b>\n\n<b>DX:</b> {call}\n<b>Banda:</b> {band}\n<b>Modo:</b> {mode}\n<b>Freq:</b> {freq}\n<b>Info:</b> <code>{comment}</code>",
        'filter_saved': "✅ Filtro guardado: {call} en {bands} ({mode}).",
        'no_recent': "<i>No se encontraron spots recientes para {call}.</i>"
    },
    'en': {
        'start': "<b>73, {name}!</b> 🎙️\nWelcome to your DX Alert bot with RBN support.",
        'help': (
            "<b>Command Guide:</b>\n\n"
            "• /setfilter [Call] [Band] [Mode] - Create alert and show history.\n"
            "• /last [Call] - Show last 10 spots (30 min).\n"
            "• /rbn [on|off] - Enable/Disable RBN (Skimmer) spots.\n"
            "• /myfilters - View active alerts.\n"
            "• /delfilter [ID] - Delete an alert.\n\n"
            "ℹ️ <i>Note: Duplicates are filtered every 10 min.</i>"
        ),
        'rbn_status': "✅ RBN spots are now: <b>{status}</b>",
        'spot': "🎯 <b>SPOT</b>\n\n<b>DX:</b> {call}\n<b>Band:</b> {band}\n<b>Mode:</b> {mode}\n<b>Freq:</b> {freq}\n<b>Info:</b> <code>{comment}</code>",
        'filter_saved': "✅ Filter saved: {call} on {bands} ({mode}).",
        'no_recent': "<i>No recent spots found for {call}.</i>"
    },
    'fr': {
        'start': "<b>73, {name}!</b> 🎙️\nBienvenue sur votre bot d'alerte DX.",
        'help': "<b>Guide:</b>\n• /setfilter [DX] [Bande] [Mode]\n• /last [DX]\n• /rbn [on|off]",
        'rbn_status': "✅ Spots RBN: <b>{status}</b>",
        'spot': "🎯 <b>SPOT</b>\n\n<b>DX:</b> {call}\n<b>Bande:</b> {band}\n<b>Mode:</b> {mode}",
        'filter_saved': "✅ Filtre enregistré: {call} ({mode}).",
        'no_recent': "<i>Aucun spot récent trouvé pour {call}.</i>"
    },
    'it': {
        'start': "<b>73, {name}!</b> 🎙️\nBenvenuto nel tuo bot DX.",
        'help': "<b>Guida:</b>\n• /setfilter [DX] [Banda] [Modo]\n• /last [DX]\n• /rbn [on|off]",
        'rbn_status': "✅ Spots RBN: <b>{status}</b>",
        'spot': "🎯 <b>SPOT</b>\n\n<b>DX:</b> {call}\n<b>Banda:</b> {band}\n<b>Modo:</b> {mode}",
        'filter_saved': "✅ Filtro salvato: {call} ({mode}).",
        'no_recent': "<i>Nessun spot trovato per {call}.</i>"
    },
    'de': {
        'start': "<b>73, {name}!</b> 🎙️\nWillkommen beim DX-Bot.",
        'help': "<b>Anleitung:</b>\n• /setfilter [DX] [Band] [Modus]\n• /last [DX]\n• /rbn [on|off]",
        'rbn_status': "✅ RBN-Spots: <b>{status}</b>",
        'spot': "🎯 <b>SPOT</b>\n\n<b>DX:</b> {call}\n<b>Band:</b> {band}\n<b>Modus:</b> {mode}",
        'filter_saved': "✅ Filter gespeichert: {call} ({mode}).",
        'no_recent': "<i>Keine aktuellen Spots für {call} gefunden.</i>"
    },
    'pt': {
        'start': "<b>73, {name}!</b> 🎙️\nBem-vindo ao bot DX.",
        'help': "<b>Guia:</b>\n• /setfilter [DX] [Banda] [Modo]\n• /last [DX]\n• /rbn [on|off]",
        'rbn_status': "✅ Spots RBN: <b>{status}</b>",
        'spot': "🎯 <b>SPOT</b>\n\n<b>DX:</b> {call}\n<b>Banda:</b> {band}\n<b>Modo:</b> {mode}",
        'filter_saved': "✅ Filtro salvo: {call} ({mode}).",
        'no_recent': "<i>Não foram encontrados spots para {call}.</i>"
    }
}

def get_text(key, lang_code, **kwargs):
    lang = lang_code[:2] if lang_code and lang_code[:2] in STRINGS else 'en'
    template = STRINGS[lang].get(key, STRINGS['en'][key])
    return template.format(**kwargs)