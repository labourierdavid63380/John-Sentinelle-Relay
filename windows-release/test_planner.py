import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'SuitePayload'/'John'))
from openai_planner import ask, needs_planner, PlannerError

def msg(t):
 return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':t}]}]}
def call(tag='diagnostic',name='pc_tool'):
 import json
 return {'status':'completed','output':[{'type':'function_call','name':name,'arguments':json.dumps({'tag':tag}),'call_id':'one'}]}
class PlannerTests(unittest.TestCase):
 def test_conversation_never_runs_tool(self):
  calls=[]
  result=ask('bonjour','test',{'diagnostic':'Diagnostic'},calls.append,requester=lambda k,p:msg('Bonjour'))
  self.assertEqual(result['message'],'Bonjour');self.assertEqual(calls,[])
 def test_valid_tool_and_result(self):
  seen=[];responses=[call(),msg('Panneau ouvert')]
  def run(tag):seen.append(tag);return {'ok':True,'state':'opened','report_path':'report.json'}
  result=ask('diagnostic','test',{'diagnostic':'Diagnostic'},run,requester=lambda k,p:responses.pop(0))
  self.assertEqual(seen,['diagnostic']);self.assertEqual(result['report_path'],'report.json')
 def test_unknown_actions_rejected(self):
  for response in [call('shell'),call(name='powershell')]:
   with self.assertRaises(PlannerError):ask('test','test',{'diagnostic':'Diagnostic'},lambda t:self.fail('executed'),requester=lambda k,p:response)
 def test_multiple_actions_rejected(self):
  response=call();response['output']*=2
  with self.assertRaises(PlannerError):ask('test','test',{'diagnostic':'Diagnostic'},lambda t:self.fail('executed'),requester=lambda k,p:response)
 def test_missing_key(self):
  self.assertFalse(ask('hi',None,{},lambda t:self.fail('executed'))['ok'])
 def test_fallback_flags(self):
  for flag in ['need_chatgpt_planner','needs_chatgpt_planner']:self.assertTrue(needs_planner({flag:True}))
 def test_cancelled_is_not_success(self):
  responses=[call(),msg('Annulé')]
  r=ask('test','test',{'diagnostic':'Diagnostic'},lambda t:{'ok':False,'state':'cancelled'},requester=lambda k,p:responses.pop(0))
  self.assertFalse(r['ok'])
 def test_incomplete_response_rejected(self):
  from openai_planner import api_request
  import io
  class Response(io.BytesIO):
   def __enter__(self):return self
   def __exit__(self,*a):self.close()
  with self.assertRaises(PlannerError):api_request('test',{},opener=lambda *a,**k:Response(b'{"status":"incomplete"}'))
if __name__=='__main__':unittest.main()
