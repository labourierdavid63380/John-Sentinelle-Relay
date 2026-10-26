import ast
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
STATE = {'local_token':'local-test', 'gateway_token':'gateway-test'}

class FakeRuntime:
    def __init__(self):
        self.local_starts=0;self.tunnel_starts=0;self.closes=0;self.stops=0
    def start(self):self.local_starts+=1
    def start_tunnel(self):self.tunnel_starts+=1
    def tunnel_status(self):return 'Prête : /readyz OK'
    def stop_tunnel(self):self.stops+=1
    def close(self):self.closes+=1

class PluginTests(unittest.TestCase):
    def setUp(self):
        self.saved=[]
        modules={
            'john_v13':types.ModuleType('john_v13'),
            'john_v13.runtime':types.SimpleNamespace(Runtime=FakeRuntime),
            'john_v13.client':types.SimpleNamespace(request=lambda:{'ok':True}),
            'john_v13.storage':types.SimpleNamespace(load_secrets=lambda:dict(STATE),save_secrets=self.saved.append),
        }
        with patch.dict(sys.modules,modules):
            spec=importlib.util.spec_from_file_location('connection_test',HERE/'patches/John/plugin_connection.py')
            self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
    def test_existing_local_server_still_starts_tunnel(self):
        c=self.m.Connection();c.probe()
        self.assertEqual(c.owned.local_starts,0)
        self.assertEqual(c.owned.tunnel_starts,1)
        self.assertTrue(c.connected)
    def test_missing_server_starts_owned_runtime(self):
        self.m.request=lambda:{'ok':False}
        c=self.m.Connection();c.probe()
        self.assertEqual(c.owned.local_starts,1)
    def test_reconnect_uses_current_tunnel_config(self):
        c=self.m.Connection();c.probe();c.reconnect()
        self.assertEqual(c.owned.stops,1)
        self.assertEqual(c.owned.tunnel_starts,2)
        c.close();self.assertEqual(c.owned.closes,1)
        c.probe();self.assertEqual(c.owned.tunnel_starts,2)
    def test_setup_preserves_local_authentication(self):
        self.m.save_connection('tunnel_test123456','runtime-test-value')
        self.assertEqual(self.saved[0]['local_token'],STATE['local_token'])
        self.assertEqual(self.saved[0]['gateway_token'],STATE['gateway_token'])
        self.assertEqual(self.saved[0]['tunnel_id'],'tunnel_test123456')
    def test_invalid_setup_does_not_write(self):
        for tid,key in [('invalid','x'),('tunnel_test123456','')]:
            with self.assertRaises(ValueError):self.m.save_connection(tid,key)
        self.assertFalse(self.saved)
    def test_error_does_not_disclose_exception_text(self):
        c=self.m.Connection();c.owned=FakeRuntime()
        c.owned.start_tunnel=Mock(side_effect=RuntimeError('sensitive-test-value'))
        c.probe()
        self.assertNotIn('sensitive-test-value',c.state)
        self.assertIn('RuntimeError',c.state)
    def test_local_commands_do_not_load_or_call_paid_api(self):
        tree=ast.parse((HERE/'patches/John/suite_john.py').read_text())
        bubble=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Bubble')
        method=next(n for n in bubble.body if isinstance(n,ast.FunctionDef) and n.name=='handle_request')
        module=ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[]))
        gui=types.SimpleNamespace(executer_demande=lambda text:{'needs_chatgpt_planner':True})
        scope={'select':lambda text:None,'gui':gui}
        exec(compile(module,'handle_request','exec'),scope)
        self.assertIn('Bonjour',scope['handle_request'](None,'bonjour John'))
        result=scope['handle_request'](None,'une demande complexe')
        self.assertIn('plugin John Sentinelle',result['message'])
        source=ast.unparse(tree)
        self.assertNotIn('load_key',source)
        self.assertNotIn('openai_planner',source)

if __name__=='__main__':unittest.main()
