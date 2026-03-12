import html

STRINGS = {
    'es': {
        'start': "<b>¡73, {name}!</b> 🎙️\nBienvenido a tu bot DX con soporte RBN.",
        'help': (
            "<b>Guía de Comandos:</b>\n\n"
            "<b>/setfilter</b>\n"
            "  /setfilter &lt;CALL&gt; - Todas las bandas, todos los modos\n"
            "  /setfilter &lt;CALL&gt; &lt;bandas&gt; - Bandas específicas, todos los modos\n"
            "  /setfilter &lt;CALL&gt; * &lt;modos&gt; - Todas las bandas, modos específicos\n"
            "  /setfilter &lt;CALL&gt; &lt;bandas&gt; &lt;modos&gt; - Bandas y modos específicos\n\n"
            "<b>Bandas:</b> 160,80,60,40,30,20,17,15,12,10,6,4,2,UHF (ej: 40,20 o ALL/*)\n"
            "<b>Modos:</b> SSB,CW,DIGI,FT8 (ej: SSB,FT8 o ALL/*)\n\n"
            "• /last [CALL] - Ver últimos 10 spots (30 min)\n"
            "• /rbn [on|off] - Activar/Desactivar RBN\n"
            "• /myfilters - Ver filtros activos (pulsa botones para borrar)\n\n"
            "• /clearallfilters - Borrar todos tus filtros\n\n"
            "• /about - Informacion del bot\n\n"
            "ℹ️ <i>Duplicados filtrados cada 10 min.</i>"
        ),
        'filter_error': "❌ Error: Formato incorrecto.\n\n<b>Uso:</b>\n/setfilter &lt;CALL&gt;\n/setfilter &lt;CALL&gt; &lt;bandas&gt;\n/setfilter &lt;CALL&gt; * &lt;modos&gt;\n/setfilter &lt;CALL&gt; &lt;bandas&gt; &lt;modos&gt;",
        'invalid_bands': "❌ Bandas inválidas. Usa: 160,80,60,40,30,20,17,15,12,10,6,4,2,UHF",
        'invalid_modes': "❌ Modos inválidos. Usa: SSB,CW,DIGI,FT8",
        'rbn_status': "✅ Spots de RBN ahora: <b>{status}</b>",
        'spot': "🎯 <b>SPOT{rbn_label}</b>\n\n<b>DX:</b> {call}\n<b>Banda:</b> {band}\n<b>Modo:</b> {mode}\n<b>Freq:</b> {freq}\n<b>Hora:</b> {time}\n<b>Origen:</b> {origin}\n<b>Info:</b> <code>{comment}</code>",
        'filter_saved': "✅ Filtro guardado: {call} en {bands} ({mode}).",
        'no_recent': "<i>No se encontraron spots recientes para {call}.</i>",
        'filters_cleared': "✅ Se han borrado <b>{count}</b> filtros.",
        'no_filters_to_clear': "ℹ️ No tienes filtros para borrar.",
        'clearall_confirm_prompt': "⚠️ Vas a borrar <b>todos</b> tus filtros.\nMientras confirmas, se pausaran temporalmente tus spots.\n\n¿Deseas continuar?",
        'clearall_confirm_yes': "✅ Confirmar",
        'clearall_confirm_no': "❌ Cancelar",
        'clearall_cancelled': "✅ Operacion cancelada. Tus spots vuelven a estar activos.",
        'clearall_expired': "ℹ️ La confirmacion ha expirado. Ejecuta /clearallfilters de nuevo.",
        'about': "<b>2026 SCQ Devices - EA1NK DXspider Telegram Bot</b>"
    },
    'en': {
        'start': "<b>73, {name}!</b> 🎙️\nWelcome to your DX Alert bot with RBN support.",
        'help': (
            "<b>Command Guide:</b>\n\n"
            "<b>/setfilter</b>\n"
            "  /setfilter &lt;CALL&gt; - All bands, all modes\n"
            "  /setfilter &lt;CALL&gt; &lt;bands&gt; - Specific bands, all modes\n"
            "  /setfilter &lt;CALL&gt; * &lt;modes&gt; - All bands, specific modes\n"
            "  /setfilter &lt;CALL&gt; &lt;bands&gt; &lt;modes&gt; - Specific bands and modes\n\n"
            "<b>Bands:</b> 160,80,60,40,30,20,17,15,12,10,6,4,2,UHF (e.g: 40,20 or ALL/*)\n"
            "<b>Modes:</b> SSB,CW,DIGI,FT8 (e.g: SSB,FT8 or ALL/*)\n\n"
            "• /last [CALL] - Show last 10 spots (30 min)\n"
            "• /rbn [on|off] - Enable/Disable RBN\n"
            "• /myfilters - View active filters (press buttons to delete)\n\n"
            "• /clearallfilters - Remove all your filters\n\n"
            "• /about - Bot information\n\n"
            "ℹ️ <i>Duplicates filtered every 10 min.</i>"
        ),
        'filter_error': "❌ Error: Invalid format.\n\n<b>Usage:</b>\n/setfilter &lt;CALL&gt;\n/setfilter &lt;CALL&gt; &lt;bands&gt;\n/setfilter &lt;CALL&gt; * &lt;modes&gt;\n/setfilter &lt;CALL&gt; &lt;bands&gt; &lt;modes&gt;",
        'invalid_bands': "❌ Invalid bands. Use: 160,80,60,40,30,20,17,15,12,10,6,4,2,UHF",
        'invalid_modes': "❌ Invalid modes. Use: SSB,CW,DIGI,FT8",
        'rbn_status': "✅ RBN spots are now: <b>{status}</b>",
        'spot': "🎯 <b>SPOT{rbn_label}</b>\n\n<b>DX:</b> {call}\n<b>Band:</b> {band}\n<b>Mode:</b> {mode}\n<b>Freq:</b> {freq}\n<b>Time:</b> {time}\n<b>Origin:</b> {origin}\n<b>Info:</b> <code>{comment}</code>",
        'filter_saved': "✅ Filter saved: {call} on {bands} ({mode}).",
        'no_recent': "<i>No recent spots found for {call}.</i>",
        'filters_cleared': "✅ Cleared <b>{count}</b> filters.",
        'no_filters_to_clear': "ℹ️ You have no filters to clear.",
        'clearall_confirm_prompt': "⚠️ You are about to remove <b>all</b> your filters.\nWhile this confirmation is pending, your spots are temporarily paused.\n\nDo you want to continue?",
        'clearall_confirm_yes': "✅ Confirm",
        'clearall_confirm_no': "❌ Cancel",
        'clearall_cancelled': "✅ Operation cancelled. Your spot delivery is active again.",
        'clearall_expired': "ℹ️ Confirmation expired. Run /clearallfilters again.",
        'about': "<b>2026 SCQ Devices - EA1NK DXspider Telegram Bot</b>"
    },
    'fr': {
        'start': "<b>73, {name}!</b> 🎙️\nBienvenue sur votre bot d'alerte DX.",
        'help': "<b>Guide:</b>\n• /setfilter [DX]\n• /setfilter [DX] [Bandes]\n• /setfilter [DX] * [Modes]\n• /setfilter [DX] [Bandes] [Modes]\n\n<b>Bandes:</b> 160,80,60,40,30,20,17,15,12,10,6,4,2,UHF (ALL/*)\n<b>Modes:</b> SSB,CW,DIGI,FT8 (ALL/*)",
        'filter_error': "❌ Erreur: Format invalide.",
        'invalid_bands': "❌ Bandes invalides. Utilisez: 160,80,60,40,30,20,17,15,12,10,6,4,2,UHF",
        'invalid_modes': "❌ Modes invalides. Utilisez: SSB,CW,DIGI,FT8",
        'rbn_status': "✅ Spots RBN: <b>{status}</b>",
        'spot': "🎯 <b>SPOT{rbn_label}</b>\n\n<b>DX:</b> {call}\n<b>Bande:</b> {band}\n<b>Mode:</b> {mode}\n<b>Freq:</b> {freq}\n<b>Heure:</b> {time}\n<b>Origine:</b> {origin}\n<b>Info:</b> <code>{comment}</code>",
        'filter_saved': "✅ Filtre enregistré: {call} ({mode}).",
        'no_recent': "<i>Aucun spot récent trouvé pour {call}.</i>",
        'filters_cleared': "✅ Cleared <b>{count}</b> filters.",
        'no_filters_to_clear': "ℹ️ You have no filters to clear."
    },
    'it': {
        'start': "<b>73, {name}!</b> 🎙️\nBenvenuto nel tuo bot DX.",
        'help': "<b>Guida:</b>\n• /setfilter [DX]\n• /setfilter [DX] [Bande]\n• /setfilter [DX] * [Modi]\n• /setfilter [DX] [Bande] [Modi]\n\n<b>Bande:</b> 160,80,60,40,30,20,17,15,12,10,6,4,2,UHF (ALL/*)\n<b>Modi:</b> SSB,CW,DIGI,FT8 (ALL/*)",
        'filter_error': "❌ Errore: Formato non valido.",
        'invalid_bands': "❌ Bande non valide. Usa: 160,80,60,40,30,20,17,15,12,10,6,4,2,UHF",
        'invalid_modes': "❌ Modi non validi. Usa: SSB,CW,DIGI,FT8",
        'rbn_status': "✅ Spots RBN: <b>{status}</b>",
        'spot': "🎯 <b>SPOT{rbn_label}</b>\n\n<b>DX:</b> {call}\n<b>Banda:</b> {band}\n<b>Modo:</b> {mode}\n<b>Freq:</b> {freq}\n<b>Ora:</b> {time}\n<b>Origine:</b> {origin}\n<b>Info:</b> <code>{comment}</code>",
        'filter_saved': "✅ Filtro salvato: {call} ({mode}).",
        'no_recent': "<i>Nessun spot trovato per {call}.</i>",
        'filters_cleared': "✅ Cleared <b>{count}</b> filters.",
        'no_filters_to_clear': "ℹ️ You have no filters to clear."
    },
    'de': {
        'start': "<b>73, {name}!</b> 🎙️\nWillkommen beim DX-Bot.",
        'help': "<b>Anleitung:</b>\n• /setfilter [DX]\n• /setfilter [DX] [Bänder]\n• /setfilter [DX] * [Modi]\n• /setfilter [DX] [Bänder] [Modi]\n\n<b>Bänder:</b> 160,80,60,40,30,20,17,15,12,10,6,4,2,UHF (ALL/*)\n<b>Modi:</b> SSB,CW,DIGI,FT8 (ALL/*)",
        'filter_error': "❌ Fehler: Ungültiges Format.",
        'invalid_bands': "❌ Ungültige Bänder. Verwenden Sie: 160,80,60,40,30,20,17,15,12,10,6,4,2,UHF",
        'invalid_modes': "❌ Ungültige Modi. Verwenden Sie: SSB,CW,DIGI,FT8",
        'rbn_status': "✅ RBN-Spots: <b>{status}</b>",
        'spot': "🎯 <b>SPOT{rbn_label}</b>\n\n<b>DX:</b> {call}\n<b>Band:</b> {band}\n<b>Modus:</b> {mode}\n<b>Freq:</b> {freq}\n<b>Zeit:</b> {time}\n<b>Ursprung:</b> {origin}\n<b>Info:</b> <code>{comment}</code>",
        'filter_saved': "✅ Filter gespeichert: {call} ({mode}).",
        'no_recent': "<i>Keine aktuellen Spots für {call} gefunden.</i>",
        'filters_cleared': "✅ Cleared <b>{count}</b> filters.",
        'no_filters_to_clear': "ℹ️ You have no filters to clear."
    },
    'pt': {
        'start': "<b>73, {name}!</b> 🎙️\nBem-vindo ao bot DX.",
        'help': "<b>Guia:</b>\n• /setfilter [DX]\n• /setfilter [DX] [Bandas]\n• /setfilter [DX] * [Modos]\n• /setfilter [DX] [Bandas] [Modos]\n\n<b>Bandas:</b> 160,80,60,40,30,20,17,15,12,10,6,4,2,UHF (ALL/*)\n<b>Modos:</b> SSB,CW,DIGI,FT8 (ALL/*)",
        'filter_error': "❌ Erro: Formato inválido.",
        'invalid_bands': "❌ Bandas inválidas. Use: 160,80,60,40,30,20,17,15,12,10,6,4,2,UHF",
        'invalid_modes': "❌ Modos inválidos. Use: SSB,CW,DIGI,FT8",
        'rbn_status': "✅ Spots RBN: <b>{status}</b>",
        'spot': "🎯 <b>SPOT{rbn_label}</b>\n\n<b>DX:</b> {call}\n<b>Banda:</b> {band}\n<b>Modo:</b> {mode}\n<b>Freq:</b> {freq}\n<b>Hora:</b> {time}\n<b>Origem:</b> {origin}\n<b>Info:</b> <code>{comment}</code>",
        'filter_saved': "✅ Filtro salvo: {call} ({mode}).",
        'no_recent': "<i>Não foram encontrados spots para {call}.</i>",
        'filters_cleared': "✅ Cleared <b>{count}</b> filters.",
        'no_filters_to_clear': "ℹ️ You have no filters to clear."
    }
}

def get_text(key, lang_code, **kwargs):
    lang = lang_code[:2] if lang_code and lang_code[:2] in STRINGS else 'en'
    template = STRINGS[lang].get(key, STRINGS['en'][key])
    kwargs.setdefault('rbn_label', '')
    kwargs.setdefault('time', 'N/A')
    kwargs.setdefault('origin', 'N/A')
    kwargs.setdefault('comment', '')
    safe_kwargs = {
        k: html.escape(str(v), quote=False) if v is not None else ''
        for k, v in kwargs.items()
    }
    return template.format(**safe_kwargs)
