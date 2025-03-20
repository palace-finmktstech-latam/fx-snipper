import React, { useState, useEffect } from 'react';
import Settings from './Settings';
import './SwapSnipper.css';

const SwapSnipper = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [tradeInfo, setTradeInfo] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [myEntity, setMyEntity] = useState('');
  const [pastedContent, setPastedContent] = useState(null);
  const [isHovered, setIsHovered] = useState(false);
  const [isPayingTableExpanded, setIsPayingTableExpanded] = useState(false);
  const [isReceivingTableExpanded, setIsReceivingTableExpanded] = useState(false);
  const [error, setError] = useState(null);
  const [tradeSentToMurex, setTradeSentToMurex] = useState(false);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    const storedEntity = localStorage.getItem('myEntity');
    setMyEntity(storedEntity || '');
  }, []);

  useEffect(() => {
    return () => {
      if (pastedContent?.type === 'image') {
        URL.revokeObjectURL(pastedContent.content);
      }
    };
  }, [pastedContent]);

  const processSwap = async (content, type) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const storedPairs = localStorage.getItem('personCompanyPairs');
      const requestBody = {
        input_type: type,
        [type === 'text' ? 'input_text' : 'input_image']: content,
        ai_provider: localStorage.getItem('aiProvider') || 'Anthropic',
        user_name: localStorage.getItem('myName') || '',
        user_entity: localStorage.getItem('myEntity') || '',
        person_company_pairs: storedPairs ? JSON.parse(storedPairs) : []
      };

      const response = await fetch('http://localhost:5001/api/process-swap', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setTradeInfo(data);
    } catch (err) {
      setError('Failed to process swap: ' + err.message);
      console.error('Error processing swap:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePaste = async (e) => {
    console.log('Paste event triggered', e);
    
    e.preventDefault();
    const items = e.clipboardData.items;
    
    for (const item of items) {
      if (item.type.indexOf('image') !== -1) {
        const file = item.getAsFile();
        const reader = new FileReader();
        
        reader.onload = async (event) => {
          const base64Image = event.target.result.split(',')[1];
          setPastedContent({
            type: 'image',
            content: URL.createObjectURL(file)
          });
          await processSwap(base64Image, 'image');
        };
        
        reader.readAsDataURL(file);
        break;
      } else if (item.type === 'text/plain') {
        item.getAsString(async (text) => {
          setPastedContent({
            type: 'text',
            content: text
          });
          await processSwap(text, 'text');
        });
        break;
      }
    }
  };

  const getCashflowData = () => {
    if (!tradeInfo || !tradeInfo.legs) return [];

    return tradeInfo.legs.flatMap((leg) =>
      leg.cashflows.map((flow) => ({
        legNumber: leg.legNumber,
        startDate: flow.startDate,
        endDate: flow.endDate,
        rate: flow.rate,
        spread: flow.spread,
        remainingCapital: flow.remainingCapital,
        amortization: flow.amortization,
        interest: flow.interest,
      }))
    );
  };

  const columnDefs = [
    { headerName: 'Leg', field: 'legNumber', sortable: true, width: 80 },
    { headerName: 'Start Date', field: 'startDate', sortable: true, filter: true, width: 120 },
    { headerName: 'End Date', field: 'endDate', sortable: true, filter: true, width: 120 },
    { headerName: 'Rate', field: 'rate', sortable: true, filter: true, width: 100 },
    { headerName: 'Spread', field: 'spread', sortable: true, filter: true, width: 100 },
    {
      headerName: 'Remaining Capital',
      field: 'remainingCapital',
      sortable: true,
      filter: true,
      width: 150,
      valueFormatter: (params) => params.value ? params.value.toLocaleString() : '',
    },
    {
      headerName: 'Amortization',
      field: 'amortization',
      sortable: true,
      filter: true,
      width: 120,
      valueFormatter: (params) => params.value ? params.value.toLocaleString() : '',
    },
    {
      headerName: 'Interest',
      field: 'interest',
      sortable: true,
      filter: true,
      width: 120,
      valueFormatter: (params) => params.value ? params.value.toLocaleString() : '',
    },
  ];

  const getTradeDetailsAsProse = () => {
    if (!tradeInfo || !tradeInfo.tradeInfo || !myEntity) return '';

    const {
      leg1Rate,
      leg1Payer,
      leg1Currency,
      leg1NotionalAmount,
      leg2Rate,
      leg2Payer,
      leg2Currency,
      leg2NotionalAmount,
    } = tradeInfo.tradeInfo;

    const formatRate = (rate) => (isNaN(rate) ? rate : `${rate}%`);

    if (myEntity === leg1Payer) {
      return (
        <>
          <strong>{myEntity}</strong> <strong>pays</strong> {formatRate(leg1Rate)} on {leg1Currency} {leg1NotionalAmount.toLocaleString()}
          {' '}and <strong>receives</strong> {formatRate(leg2Rate)} on {leg2Currency} {leg1NotionalAmount.toLocaleString()} from <strong>{leg2Payer}</strong>.
        </>
      );
    }

    if (myEntity === leg2Payer) {
      return (
        <>
          <strong>{myEntity}</strong> <strong>pays</strong> {formatRate(leg2Rate)} on {leg2Currency} {leg2NotionalAmount.toLocaleString()}
          {' '}<strong>and receives</strong> {formatRate(leg1Rate)} on {leg1Currency} {leg2NotionalAmount.toLocaleString()} from <strong>{leg1Payer}</strong>.
        </>
      );
    }

    return 'Entity does not match either payer in the trade.';
  };

  const getCashflowTables = () => {
    if (!tradeInfo || !tradeInfo.legs) {
      return { myEntityFlows: [], otherEntityFlows: [], myEntityLabel: '', otherEntityLabel: '' };
    }

    let myEntityFlows = [];
    let otherEntityFlows = [];
    let myEntityLabel = '';
    let otherEntityLabel = '';

    const payingLeg = tradeInfo.legs.find(leg => leg.payer === myEntity);
    const receivingLeg = tradeInfo.legs.find(leg => leg.payer !== myEntity);

    if (payingLeg) {
      myEntityFlows = payingLeg.cashflows;
      otherEntityFlows = receivingLeg.cashflows;
    } else {
      myEntityFlows = receivingLeg.cashflows;
      otherEntityFlows = payingLeg.cashflows;
    }

    myEntityLabel = `${myEntity} pays:`;
    otherEntityLabel = `${myEntity} receives:`;

    return { myEntityFlows, otherEntityFlows, myEntityLabel, otherEntityLabel };
  };

  const downloadJSON = () => {
    const element = document.createElement('a');
    const file = new Blob([JSON.stringify(tradeInfo, null, 2)], { type: 'application/json' });
    element.href = URL.createObjectURL(file);
    element.download = 'detected_trade.json';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const headerStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: '1px solid #00e7ff',
    paddingBottom: '5px',
    fontSize: '10px'
  };

  const toggleButtonStyle = {
    background: 'none',
    border: 'none',
    color: '#00e7ff',
    cursor: 'pointer',
    padding: '0 5px',
    fontSize: '14px'
  };

  return (
    <div
      style={{
        backgroundColor: 'black',
        color: 'white',
        height: '100vh',
        fontFamily: 'Manrope, sans-serif',
        cursor: isLoading || isSending ? 'wait' : 'default',
        display: 'flex',
        flexDirection: 'column',
        overflowX: 'hidden',
        maxWidth: '100vw',
        padding: '20px',
        boxSizing: 'border-box',
      }}
    >
      {/* Top Section */}
      <div
        style={{
          width: '100%',
          height: '60px',
          padding: '10px',
          backgroundColor: '#1a1a1a',
          borderBottom: '1px solid #00e7ff',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          overflow: 'visible',
          position: 'relative',
          zIndex: 10,
        }}
      >
        <img src="palace_blanco.png" alt="Logo" style={{ height: '40px', marginRight: '10px' }} />
        
        <div
          style={{
            flex: 1,
            margin: '0 15px',
            padding: '8px',
            border: '1px solid #00e7ff',
            borderRadius: '4px',
            maxHeight: '20px',
            minHeight: '20px',
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            color: 'white',
            backgroundColor: '#1f1f1f',
            fontSize: '9px',
          }}
          onClick={async () => {
            try {
              const clipboardItems = await navigator.clipboard.read();
              for (const clipboardItem of clipboardItems) {
                // Check for image types
                if (clipboardItem.types.some(type => type.startsWith('image/'))) {
                  const imageType = clipboardItem.types.find(type => type.startsWith('image/'));
                  const blob = await clipboardItem.getType(imageType);
                  const reader = new FileReader();
                  reader.onload = async (event) => {
                    const base64Image = event.target.result.split(',')[1];
                    setPastedContent({
                      type: 'image',
                      content: URL.createObjectURL(blob)
                    });
                    await processSwap(base64Image, 'image');
                  };
                  reader.readAsDataURL(blob);
                  break;
                } 
                // Check for text
                else if (clipboardItem.types.includes('text/plain')) {
                  const text = await (await clipboardItem.getType('text/plain')).text();
                  setPastedContent({
                    type: 'text',
                    content: text
                  });
                  await processSwap(text, 'text');
                  break;
                }
              }
            } catch (err) {
              console.error('Failed to read clipboard contents: ', err);
              // Fallback to the paste event if clipboard API fails
              alert('Please use Ctrl+V or right-click and paste');
            }
          }}
          onPaste={handlePaste}
        >
          {pastedContent ? (
            pastedContent.type === 'image' ? (
              <div 
                style={{ 
                  position: 'relative',
                  height: '18px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
              >
                <img 
                  src={pastedContent.content}
                  alt=""
                  style={{ 
                    maxHeight: '18px',
                    width: 'auto',
                    cursor: 'pointer'
                  }} 
                />
                {isHovered && (
                  <div style={{
                    position: 'fixed',
                    top: '60px',
                    left: '10px',
                    zIndex: 2000,
                    padding: '10px',
                    background: '#1a1a1a',
                    border: '1px solid #00e7ff',
                    borderRadius: '4px',
                    boxShadow: '0 4px 8px rgba(0,0,0,0.5)'
                  }}>
                    <img 
                      src={pastedContent.content}
                      alt=""
                      style={{ 
                        maxWidth: '400px',
                        maxHeight: '400px',
                        width: 'auto',
                        height: 'auto'
                      }} 
                    />
                  </div>
                )}
              </div>
            ) : (
              <div
                style={{ 
                  position: 'relative',
                  display: 'inline-block'
                }}
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
              >
                <span style={{ wordBreak: 'break-word' }}>
                  {pastedContent.content.substring(0, 50)}
                  {pastedContent.content.length > 50 ? '...' : ''}
                </span>

                {isHovered && (
                  <div style={{
                    position: 'fixed',
                    top: '60px',
                    left: '10px',
                    zIndex: 2000,
                    padding: '15px',
                    background: '#1a1a1a',
                    border: '1px solid #00e7ff',
                    borderRadius: '4px',
                    boxShadow: '0 4px 8px rgba(0,0,0,0.5)',
                    maxWidth: '400px',
                    maxHeight: '400px',
                    overflow: 'auto',
                    fontSize: '14px',
                    lineHeight: '1.5',
                    whiteSpace: 'pre-wrap'
                  }}>
                    {pastedContent.content}
                  </div>
                )}
              </div>
            )
          ) : (
            'Click to paste content here.'
          )}
        </div>

        <button
          onClick={() => setShowSettings(true)}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: '#00e7ff',
            fontSize: '20px',
          }}
        >
          ⚙️
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div style={{ 
          textAlign: 'center', 
          marginTop: '20px', 
          color: '#ff4444', 
          fontSize: '14px',
          padding: '10px',
          backgroundColor: 'rgba(255, 0, 0, 0.1)',
          borderRadius: '4px'
        }}>
          {error}
        </div>
      )}

      {/* Loading Indicator */}
      {isLoading && (
        <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '12px', color: '#00e7ff' }}>
          Processing swap...
        </div>
      )}

      {/* Main content container */}
      <div style={{
        height: 'calc(100% - 60px)', // Subtract header height
        overflowY: 'auto',
        paddingBottom: '60px',
      }} className="custom-scrollbar">
        {/* Trade Information Section */}
        {!isLoading && tradeInfo && (
          <>
            <div style={{ marginTop: '20px', color: 'white', fontSize: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <h3 style={{ margin: 0, fontSize: '14px', color: 'white' }}>Detected Trade</h3>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <span
                    style={{
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      backgroundColor: 'transparent',
                      transition: 'opacity 0.3s, transform 0.2s',
                      opacity: 0.8,
                    }}
                    onClick={downloadJSON}
                    title="Download JSON"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#00e7ff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ width: '20px', height: '20px' }}>
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div>{getTradeDetailsAsProse()}</div>
                <button
                    onClick={() => {
                      if (window.confirm('Are you sure you want to delete this trade?')) {
                        setTradeInfo(null);
                        setPastedContent(null);
                        setError(null);
                      }
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: '#ff4444',
                      fontSize: '16px',
                      padding: 0,
                      display: 'flex',
                      alignItems: 'center'
                    }}
                    title="Delete trade"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#00e7ff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ width: '12px', height: '12px' }}>
                      <path d="M3 6h18" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
                      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
              </div>
            </div>

            {/* Cashflow Tables */}
            {myEntity && (
              <>
                {[
                  { 
                    label: getCashflowTables().myEntityLabel, 
                    flows: getCashflowTables().myEntityFlows,
                    isExpanded: isPayingTableExpanded,
                    setExpanded: setIsPayingTableExpanded
                  },
                  { 
                    label: getCashflowTables().otherEntityLabel, 
                    flows: getCashflowTables().otherEntityFlows,
                    isExpanded: isReceivingTableExpanded,
                    setExpanded: setIsReceivingTableExpanded
                  }
                ].map((tableData, index) => (
                  <div key={index} style={{ marginTop: '20px' }}>
                    <div style={headerStyle}>
                      <h4 style={{ margin: 0 }}>{tableData.label}</h4>
                      <button 
                        onClick={() => tableData.setExpanded(!tableData.isExpanded)}
                        style={toggleButtonStyle}
                      >
                        {tableData.isExpanded ? '−' : '+'}
                      </button>
                    </div>
                    {tableData.isExpanded && (
                      <>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '8px', marginBottom: '10px' }}>
                          <thead>
                            <tr style={{ borderBottom: '1px solid #00e7ff' }}>
                              {['Start Date', 'End Date', 'Rate', 'Spread', 'Remaining K', 'Amortization', 'Interest'].map(
                                (header, idx) => (
                                  <th key={idx} style={{ textAlign: 'left', padding: '3px' }}>
                                    {header}
                                  </th>
                                )
                              )}
                            </tr>
                          </thead>
                          <tbody>
                            {tableData.flows.map((flow, idx) => (
                              <tr key={idx} style={{ borderBottom: '1px solid #333' }}>
                                <td style={{ padding: '3px' }}>{flow.startDate}</td>
                                <td style={{ padding: '3px' }}>{flow.endDate}</td>
                                <td style={{ padding: '3px' }}>{flow.rate}</td>
                                <td style={{ padding: '3px' }}>{flow.spread}</td>
                                <td style={{ padding: '3px' }}>{flow.remainingCapital.toLocaleString()}</td>
                                <td style={{ padding: '3px' }}>{flow.amortization.toLocaleString()}</td>
                                <td style={{ padding: '3px' }}>{typeof flow.interest === 'number' ? flow.interest.toLocaleString() : flow.interest}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        <div style={{ fontSize: '8px', color: '#888', marginBottom: '20px' }}>
                          {index === 0 ? (
                            <>
                              Business Day Convention: {tradeInfo.tradeInfo.leg1BusinessDayConvention} • 
                              Day Count Convention: {tradeInfo.tradeInfo.leg1DayCountConvention}
                            </>
                          ) : (
                            <>
                              Business Day Convention: {tradeInfo.tradeInfo.leg2BusinessDayConvention} • 
                              Day Count Convention: {tradeInfo.tradeInfo.leg2DayCountConvention}
                            </>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                ))}
              </>
            )}
          </>
        )}
      </div>

      {/* Send to Murex button - ensure it's positioned at the bottom */}
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        padding: '16px',
        backgroundColor: '#1a1a1a',
        borderTop: '1px solid #2d2d2d',
        textAlign: 'right',
      }}>
        {!isLoading && tradeInfo && !tradeSentToMurex && (
          <button
            onClick={() => {
              if (window.confirm('Are you sure you want to send this trade to Murex?')) {
                setTradeSentToMurex(true);
                setIsSending(true);
                setTimeout(() => {
                  setIsSending(false);
                  alert('Trade successfully sent to Murex');
                  setTradeInfo(null);
                  setPastedContent(null);
                  setError(null);
                  setTradeSentToMurex(false);
                }, 2000);
              }
            }}
            style={{
              backgroundColor: '#00e7ff',
              color: 'black',
              border: 'none',
              borderRadius: '4px',
              padding: '8px 16px',
              cursor: 'pointer',
              fontSize: '10px',
              fontWeight: 'bold',
              transition: 'background-color 0.2s',
            }}
          >
            Send to Murex
          </button>
        )}
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <Settings onClose={() => setShowSettings(false)} />
        </div>
      )}
    </div>
  );
};

export default SwapSnipper;