"""Real nlohmann parse regression with the exact application locale override."""
import os,pathlib,resource,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
source=(root/'ps5/app/compat_app.c').read_text();function=source[source.index('struct lconv *localeconv(void) {'):]
header=root/'third_party/llama.cpp/vendor/nlohmann/json.hpp'
assert header.is_file(),'Initialize pinned llama.cpp submodule first'
program='#include <cassert>\n#include "'+str(header)+'"\nint main(){auto j=nlohmann::json::parse(R"({"temperature":0.7,"top_p":0.95,"nested":[0.2,1e-3,0.0]})");assert(j["temperature"].get<double>()==0.7);assert(j["nested"][1].get<double>()==0.001);}\n'
def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
with tempfile.TemporaryDirectory() as directory:
 p=pathlib.Path(directory);(p/'main.cpp').write_text(program)
 for broken in (True,False):
  c='#include <limits.h>\n#include <locale.h>\n'+function
  if broken:c=c.replace('.decimal_point = "."','.decimal_point = ""')
  (p/'locale.c').write_text(c)
  subprocess.run([os.getenv('CC','cc'),'-std=c11','-c',str(p/'locale.c'),'-o',str(p/'locale.o')],check=True)
  subprocess.run([os.getenv('CXX','c++'),'-std=c++17',str(p/'main.cpp'),str(p/'locale.o'),'-o',str(p/'test')],check=True)
  result=subprocess.run([str(p/'test')],cwd=p,stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec_fn=no_core)
  if broken:assert result.returncode!=0,'Negative control unexpectedly passed'
  else:assert result.returncode==0,result.stderr.decode(errors='replace')
  print(('Empty separator negative control' if broken else 'Exact application override')+': expected outcome observed',flush=True)
