import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Send, Power, Settings, History, Cpu, HardDrive, Wifi, WifiOff, Activity } from 'lucide-react';

const ReactTerminalConnected = () => {
  const [command, setCommand] = useState('');
  const [output, setOutput] = useState([{ type: 'system', content: 'Type "help" for available commands.' }]);
  const [isConnected, setIsConnected] = useState(false);
  const [currentDir, setCurrentDir] = useState('~');
  const [commandHistory, setCommandHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [isLoading, setIsLoading] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [systemStats, setSystemStats] = useState({ cpu: 0, memory: 0, disk: 0 });
  const [sessionId, setSessionId] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [processes, setProcesses] = useState([]);
  const [backendUrl, setBackendUrl] = useState('http://localhost:8000');

  const terminalRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (terminalRef.current) terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
  }, [output]);

  useEffect(() => {
    initializeTerminal();
  }, []);

  const addToOutput = (type, content) => {
    setOutput(prev => [...prev, { type, content, timestamp: new Date() }]);
  };

  const testBackendConnection = async () => {
    const testUrls = ['http://localhost:8000', 'http://127.0.0.1:8000'];
    for (const url of testUrls) {
      try {
        const response = await fetch(`${url}/api/health`, { method: 'GET', headers: { 'Content-Type': 'application/json' }, mode: 'cors' });
        if (response.ok) {
          setBackendUrl(url);
          return { success: true, url };
        }
      } catch (error) {
        console.error(`Failed to connect to ${url}:`, error.message);
      }
    }
    return { success: false };
  };

  const initializeTerminal = async () => {
    try {
      setConnectionStatus('connecting');

      const connectionTest = await testBackendConnection();
      if (!connectionTest.success) throw new Error('Backend unreachable. Demo mode enabled.');

      setConnectionStatus('connected');
      setIsConnected(true);

      const response = await fetch(`${connectionTest.url}/api/terminal/new`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        mode: 'cors'
      });
      const data = await response.json();

      if (data.success) {
        setSessionId(data.session_id);
        setCurrentDir(data.current_directory);
        await loadCommandHistory(data.session_id);
      } else throw new Error(data.error || 'Failed to create session');
    } catch (error) {
      console.error(error);
      setConnectionStatus('error');
      setIsConnected(false);
    }
  };

  const loadCommandHistory = async (sessionId) => {
    if (!sessionId) return;
    try {
      const response = await fetch(`${backendUrl}/api/terminal/history/${sessionId}`, { headers: { Accept: 'application/json' }, mode: 'cors' });
      if (response.ok) {
        const data = await response.json();
        if (data.success) setCommandHistory(data.history);
      }
    } catch (error) {
      console.error('Failed to load command history:', error);
    }
  };

  const executeCommand = async (cmd) => {
    if (!cmd.trim()) return;
    setIsLoading(true);

    const newHistory = [...commandHistory, cmd];
    setCommandHistory(newHistory);
    setHistoryIndex(-1);

    addToOutput('command', `user@terminal:${currentDir}$ ${cmd}`);

    try {
      if (isConnected && sessionId) {
        const response = await fetch(`${backendUrl}/api/terminal/execute`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          mode: 'cors',
          body: JSON.stringify({ command: cmd, session_id: sessionId })
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success) {
            if (data.current_directory !== currentDir) setCurrentDir(data.current_directory);
            if (data.output) addToOutput('output', data.output);
            if (cmd.trim() === 'clear') setOutput([]);
          } else addToOutput('error', data.output || 'Command execution failed.');
        } else {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
      } else await simulateCommand(cmd);
    } catch (error) {
      console.error(error);
      addToOutput('error', `Error: ${error.message}`);
      await simulateCommand(cmd);
    }

    setIsLoading(false);
  };

  const simulateCommand = async (cmd) => {
    await new Promise(resolve => setTimeout(resolve, 300 + Math.random() * 700));
    const cmdLower = cmd.toLowerCase().trim();

    if (cmdLower === 'help') addToOutput('output', `Available commands: pwd, ls, cd, mkdir, rm, cp, mv, cat, touch, find, cpu, mem, ps, stats, history, whoami, date, clear, help`);
    else if (cmdLower === 'ps') addToOutput('output', 'Demo process list:\nPID    NAME\n1234   demo_process\n5678   another_demo');
    else if (cmdLower === 'stats') addToOutput('output', 'Demo stats:\nCPU: 25%\nMemory: 60%\nDisk: 45%');
    else if (cmdLower === 'clear') setOutput([{ type: 'system', content: 'Type "help" for available commands.' }]);
    else if (cmdLower === 'date') addToOutput('output', new Date().toString());
    else if (cmdLower === 'whoami') addToOutput('output', 'demo_user');
    else addToOutput('output', `Demo mode: Command '${cmd}' would run on real system.`);
  };

  const focusInput = () => inputRef.current?.focus();
  const handleSubmit = () => { if (command.trim() && !isLoading) { executeCommand(command); setCommand(''); } };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (historyIndex < commandHistory.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setCommand(commandHistory[commandHistory.length - 1 - newIndex] || '');
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setCommand(commandHistory[commandHistory.length - 1 - newIndex] || '');
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setCommand('');
      }
    }
  };

  const getConnectionIcon = () => {
    switch (connectionStatus) {
      case 'connected': return <Wifi className="w-4 h-4 text-green-400" />;
      case 'connecting': return <Activity className="w-4 h-4 text-yellow-400 animate-pulse" />;
      default: return <WifiOff className="w-4 h-4 text-red-400" />;
    }
  };

  const getConnectionColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'text-green-400';
      case 'connecting': return 'text-yellow-400';
      default: return 'text-red-400';
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-green-400 font-mono">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <Terminal className="w-6 h-6 text-green-400" />
          <span className="text-lg font-semibold">Enhanced Terminal</span>
          <div className={`flex items-center space-x-2 ${getConnectionColor()}`}>
            {getConnectionIcon()}
            <span className="text-sm capitalize">{connectionStatus}</span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {showStats && (
            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center space-x-1"><Cpu className="w-4 h-4" /><span>{systemStats.cpu}%</span></div>
              <div className="flex items-center space-x-1"><HardDrive className="w-4 h-4" /><span>{systemStats.memory}%</span></div>
            </div>
          )}
          <button onClick={() => { setShowStats(!showStats); }} className="p-2 hover:bg-gray-700 rounded-md transition-colors"><Settings className="w-5 h-5" /></button>
          <button onClick={() => { const historyOutput = commandHistory.map((cmd, idx) => `${(idx + 1).toString().padStart(4)}: ${cmd}`).join('\n'); addToOutput('output', `Command History:\n${historyOutput}`); }} className="p-2 hover:bg-gray-700 rounded-md transition-colors"><History className="w-5 h-5" /></button>
          <button onClick={initializeTerminal} className="p-2 hover:bg-gray-700 rounded-md transition-colors"><Power className="w-5 h-5" /></button>
        </div>
      </div>

      {/* Terminal Content */}
      <div className="flex flex-col h-[calc(100vh-4rem)]">
        <div ref={terminalRef} className="flex-1 overflow-y-auto p-4 space-y-1 cursor-text" onClick={focusInput}>
          {output.map((item, index) => (
            <div key={index} className="break-words">
              {item.type === 'system' && <div className="text-cyan-400 text-sm"># {item.content}</div>}
              {item.type === 'command' && <div className="text-green-400 font-semibold">{item.content}</div>}
              {item.type === 'output' && <div className="text-gray-300 whitespace-pre-line ml-4">{item.content}</div>}
              {item.type === 'error' && <div className="text-red-400 whitespace-pre-line ml-4">{item.content}</div>}
            </div>
          ))}
          {isLoading && <div className="flex items-center space-x-2 text-yellow-400 ml-4"><div className="animate-spin rounded-full h-4 w-4 border-2 border-yellow-400 border-t-transparent"></div><span>Processing...</span></div>}
        </div>

        <div className="bg-gray-800 border-t border-gray-700 p-4">
          <div className="flex items-center space-x-3">
            <span className="text-green-400 font-semibold flex-shrink-0">user@terminal:{currentDir}$</span>
            <input ref={inputRef} type="text" value={command} onChange={(e) => setCommand(e.target.value)} onKeyDown={(e) => { handleKeyDown(e); if (e.key === 'Enter') handleSubmit(); }} className="flex-1 bg-transparent text-green-400 outline-none font-mono" placeholder={isConnected ? "Enter command or natural language..." : "Backend disconnected - demo mode"} disabled={isLoading} autoFocus />
            <button onClick={handleSubmit} disabled={isLoading || !command.trim()} className="p-2 hover:bg-gray-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"><Send className="w-5 h-5" /></button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReactTerminalConnected;
