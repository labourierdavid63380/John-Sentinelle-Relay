"""OpenAI companion adapter. Never changes the V24 gateway or executes model code."""
import json
import os
import urllib.error
import urllib.request

API = 'https://api.openai.com/v1/responses'
MODEL = 'gpt-4.1-mini'

class PlannerError(RuntimeError):
    pass

def api_request(key, payload, opener=None):
    request = urllib.request.Request(API, data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
    try:
        with (opener or urllib.request.urlopen)(request, timeout=45) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        messages = {401: 'Clé OpenAI refusée. Ouvrez Connexion IA.',
                    403: 'Accès OpenAI refusé pour ce projet.',
                    429: 'Quota ou limite OpenAI atteint. Vérifiez les crédits API du projet.'}
        raise PlannerError(messages.get(exc.code, 'Service OpenAI indisponible (HTTP %d).' % exc.code)) from None
    except (OSError, ValueError):
        raise PlannerError('Connexion OpenAI impossible. Vérifiez Internet puis réessayez.') from None
    if data.get('status') != 'completed':
        raise PlannerError('La réponse OpenAI est incomplète. Aucune action exécutée.')
    return data

def ask(text, key, catalog, runner, history=None, requester=api_request):
    if not key:
        return {'ok': False, 'message': 'Connexion IA à configurer : cliquez sur Connexion IA. Les outils locaux restent disponibles.'}
    tools = [{'type': 'function', 'name': 'pc_tool',
        'description': 'Ouvrir ou exécuter un outil PC Sentinelle. Le résultat réel fait foi.',
        'strict': True, 'parameters': {'type': 'object',
            'properties': {'tag': {'type': 'string', 'enum': sorted(catalog)}},
            'required': ['tag'], 'additionalProperties': False}}]
    instructions = (
        'Tu es John, assistant local. Réponds en français simplement. '
        'Pour une salutation ou une discussion, réponds directement sans outil. '
        'Tu ne disposes que des outils PC listés. Ne prétends pas avoir agi sans résultat. '
        'Si un outil indique opened, explique que le panneau est ouvert et qu’une intervention peut être nécessaire. '
        'Les résultats cancelled, error ou ok=false ne sont jamais un succès. '
        'Ne demande jamais le mot de passe ChatGPT. Aucun shell, code ou accès arbitraire aux fichiers. '
        'Ne lance aucun outil pour une question explicative, une négation ou une demande ambiguë. '
        'Catalogue : ' + json.dumps(catalog, ensure_ascii=False))
    context = list(history or [])[-12:] + [{'role': 'user', 'content': text[:12000]}]
    payload = {'model': os.environ.get('JOHN_OPENAI_MODEL', MODEL), 'store': False,
               'instructions': instructions, 'input': context, 'tools': tools,
               'parallel_tool_calls': False, 'max_output_tokens': 900}
    first = requester(key, payload)
    output = first.get('output', [])
    calls = [item for item in output if item.get('type') == 'function_call']
    if len(calls) > 1:
        raise PlannerError('Plusieurs actions proposées. Reformulez une seule demande ; aucune action exécutée.')
    result = None
    if calls:
        call = calls[0]
        try:
            args = json.loads(call['arguments'])
            valid = call.get('name') == 'pc_tool' and isinstance(args, dict) and set(args) == {'tag'} and args['tag'] in catalog
        except (KeyError, ValueError, TypeError):
            valid = False
        if not valid:
            raise PlannerError('Action IA inconnue ou invalide. Aucune action exécutée.')
        result = runner(args['tag'])
        followup = dict(payload)
        followup['input'] = context + output + [{'type': 'function_call_output',
            'call_id': call['call_id'], 'output': json.dumps(result, ensure_ascii=False, default=str)[:24000]}]
        followup['tool_choice'] = 'none'
        try:
            output = requester(key, followup).get('output', [])
        except PlannerError:
            return {'ok': bool(isinstance(result, dict) and result.get('ok')), 'message':
                'L’outil a répondu, mais le résumé IA est indisponible.', 'tool_result': result}
    message = '\n'.join(part.get('text', '') for item in output if item.get('type') == 'message'
                        for part in item.get('content', []) if part.get('type') == 'output_text').strip()
    if not message:
        raise PlannerError('Aucune réponse texte reçue. Aucun succès confirmé.')
    answer = {'ok': True, 'message': message}
    if result is not None:
        answer['tool_result'] = result
        answer['ok'] = isinstance(result, dict) and result.get('ok', result.get('state') == 'completed')
        if isinstance(result, dict) and result.get('report_path'):
            answer['report_path'] = result['report_path']
    return answer

def needs_planner(value):
    return isinstance(value, dict) and bool(value.get('need_chatgpt_planner') or value.get('needs_chatgpt_planner'))
