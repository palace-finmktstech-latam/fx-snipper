import React, { useState, useEffect } from 'react';
import Settings from './Settings';
import './FXSnipper.css';

const FXSnipper = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [tradeInfo, setTradeInfo] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [myEntity, setMyEntity] = useState('');
  const [pastedContent, setPastedContent] = useState(null);
  const [isHovered, setIsHovered] = useState(false);
  const [error, setError] = useState(null);
  const [tradeSentToMurex, setTradeSentToMurex] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [showCurrencyMenu, setShowCurrencyMenu] = useState({
    visible: false,
    currencyNumber: null,
    position: { top: 0, left: 0 }
  });

  // Currency options
  const currencyOptions = ["CLP", "CLF", "USD", "EUR", "CHF"];

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

  useEffect(() => {
    console.log('tradeInfo updated:', tradeInfo);
  }, [tradeInfo]);

  useEffect(() => {
    if (showCurrencyMenu.visible) {
      const handleClickOutside = (event) => {
        // Check if the click is outside the currency menu
        const menu = document.querySelector('.currency-menu');
        if (menu && !menu.contains(event.target)) {
          setShowCurrencyMenu({ visible: false, currencyNumber: null, position: { top: 0, left: 0 } });
        }
      };
      
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showCurrencyMenu.visible]);

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

      const response = await fetch('http://localhost:5008/api/process-fx', {
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
      
      console.log(data);
      setTradeInfo(data);
    } catch (err) {
      setError('Failed to process trade: ' + err.message);
      console.error('Error processing trade:', err);
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

  const handleTermClick = (type, value, currencyNumber, event) => {
    console.log(`Clicked on ${type}: ${value}`);
    
    switch (type) {
      case 'action':
        console.log(`Action value: "${value}", checking against 'buys' and 'sells'`);
        if (value === 'buys' || value === 'sells') {
          console.log('Calling swapTradeEntities');
          swapTradeEntities();
        }
        break;
      case 'rate':
        // For FX, this could open a rate editor in the future
        alert(`You clicked on rate: ${value}`);
        break;
      case 'currency':
        // Position the menu near the clicked element
        const rect = event.currentTarget.getBoundingClientRect();
        setShowCurrencyMenu({
          visible: true,
          currencyNumber,
          position: { 
            top: rect.bottom + window.scrollY, 
            left: rect.left + window.scrollX 
          }
        });
        break;
      case 'amount':
        // Future implementation for amount editing
        alert(`You clicked on amount: ${value}`);
        break;
      default:
        break;
    }
  };

  const swapTradeEntities = () => {
    if (!tradeInfo || !tradeInfo.TradeSummary) return;
    
    // Create a deep copy to avoid mutation issues
    const newTradeInfo = JSON.parse(JSON.stringify(tradeInfo));
    
    // For FX trades, swapping entities means changing the Direction
    const { Direction } = newTradeInfo.TradeSummary;
    
    
    // Reverse the direction - fixed the comparison
    newTradeInfo.TradeSummary.Direction = Direction.toLowerCase() === "sell" ? "Buy" : "Sell";
    
    // Update the state
    setTradeInfo(newTradeInfo);
  };

  // Handle currency selection
  const handleCurrencySelect = (currency, event) => {
    if (!tradeInfo || !showCurrencyMenu.currencyNumber) return;
    
    // Stop propagation to prevent the menu from closing immediately
    event.stopPropagation();
    
    const newTradeInfo = JSON.parse(JSON.stringify(tradeInfo));
    const currencyKey = showCurrencyMenu.currencyNumber === 1 ? 'Currency 1' : 'Currency 2';
    
    // Update the currency in TradeSummary
    newTradeInfo.TradeSummary[currencyKey] = currency;
    
    setTradeInfo(newTradeInfo);
    
    // Use setTimeout to allow the click event to complete before hiding menu
    setTimeout(() => {
      setShowCurrencyMenu({ visible: false, currencyNumber: null, position: { top: 0, left: 0 } });
    }, 50);
  };

  const getTradeDetailsAsProse = () => {
    if (!tradeInfo || !tradeInfo.TradeSummary || !myEntity) return '';

    const {
      "Currency 1": Currency1,
      "Currency 2": Currency2,
      Direction,
      "Notional Amount": notionalAmount,
      Maturity,
      "Price Maker": priceMaker,
      "Price Taker": priceTaker,
      Prices,
      "Trade Date": tradeDate,
    } = tradeInfo.TradeSummary;

    // Helper function to create clickable elements
    const makeClickable = (term, value, type, currencyNumber = null) => (
      <span 
        onClick={(e) => handleTermClick(type, value, currencyNumber, e)}
        style={{
          cursor: 'pointer',
          //textDecoration: 'underline',
          //color: '#00e7ff'
        }}
      >
        {value}
      </span>
    );

    // Determine if myEntity is the price maker or price taker
    const isMyEntityPriceMaker = myEntity === priceMaker.Company;
    const counterparty = isMyEntityPriceMaker ? priceTaker.Company : priceMaker.Company;
    
    // Calculate the amount in Currency2 based on the forward price
    const forwardPrice = Prices["Forward Price"] !== "Not Mentioned" ? Prices["Forward Price"] : Prices["Spot Price"];
    const currency2Amount = notionalAmount * forwardPrice;
    
    // Determine the correct direction and currencies based on who is who
    if (isMyEntityPriceMaker) {
      // Price maker perspective
      if (Direction === "Sell") {
        // Price maker is selling Currency1, buying Currency2
        return (
          <>
            <strong>{myEntity}</strong> <strong>{makeClickable('sells', 'sells', 'action')}</strong> {makeClickable(Currency1, Currency1, 'currency', 1)} {makeClickable(notionalAmount, notionalAmount.toLocaleString(), 'amount', 1)}
            {' '}and <strong>{makeClickable('buys', 'buys', 'action')}</strong> {makeClickable(Currency2, Currency2, 'currency', 2)} {makeClickable(currency2Amount, currency2Amount.toLocaleString(), 'amount', 2)} at {makeClickable(forwardPrice, forwardPrice, 'rate')} with <strong>{counterparty}</strong>
            {Maturity !== "Not Mentioned" && ` on ${Maturity}`}.
          </>
        );
      } else {
        // Price maker is buying Currency1, selling Currency2
        return (
          <>
            <strong>{myEntity}</strong> <strong>{makeClickable('buys', 'buys', 'action')}</strong> {makeClickable(Currency1, Currency1, 'currency', 1)} {makeClickable(notionalAmount, notionalAmount.toLocaleString(), 'amount', 1)}
            {' '}and <strong>{makeClickable('sells', 'sells', 'action')}</strong> {makeClickable(Currency2, Currency2, 'currency', 2)} {makeClickable(currency2Amount, currency2Amount.toLocaleString(), 'amount', 2)} at {makeClickable(forwardPrice, forwardPrice, 'rate')} with <strong>{counterparty}</strong>
            {Maturity !== "Not Mentioned" && ` on ${Maturity}`}.
          </>
        );
      }
    } else {
      // Price taker perspective - opposite of price maker's direction
      if (Direction === "Sell") {
        // Price taker is buying Currency1, selling Currency2
        return (
          <>
            <strong>{myEntity}</strong> <strong>{makeClickable('buys', 'buys', 'action')}</strong> {makeClickable(Currency1, Currency1, 'currency', 1)} {makeClickable(notionalAmount, notionalAmount.toLocaleString(), 'amount', 1)}
            {' '}and <strong>{makeClickable('sells', 'sells', 'action')}</strong> {makeClickable(Currency2, Currency2, 'currency', 2)} {makeClickable(currency2Amount, currency2Amount.toLocaleString(), 'amount', 2)} at {makeClickable(forwardPrice, forwardPrice, 'rate')} with <strong>{counterparty}</strong>
            {Maturity !== "Not Mentioned" && ` settling on ${Maturity}`}.
          </>
        );
      } else {
        // Price taker is selling Currency1, buying Currency2
        return (
          <>
            <strong>{myEntity}</strong> <strong>{makeClickable('sells', 'sells', 'action')}</strong> {makeClickable(Currency1, Currency1, 'currency', 1)} {makeClickable(notionalAmount, notionalAmount.toLocaleString(), 'amount', 1)}
            {' '}and <strong>{makeClickable('buys', 'buys', 'action')}</strong> {makeClickable(Currency2, Currency2, 'currency', 2)} {makeClickable(currency2Amount, currency2Amount.toLocaleString(), 'amount', 2)} at {makeClickable(forwardPrice, forwardPrice, 'rate')} with <strong>{counterparty}</strong>
            {Maturity !== "Not Mentioned" && ` settling on ${Maturity}`}.
          </>
        );
      }
    }
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
          Processing FX trade...
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
                <h3 style={{ margin: 0, fontSize: '14px', color: 'white' }}>
                  {tradeInfo.TradeSummary.Prices["Forward Price"] && tradeInfo.TradeSummary.Prices["Forward Price"] !== "Not Mentioned" 
                    ? "Detected FX Forward Trade" 
                    : "Detected FX Spot Trade"}
                </h3>
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

            {/* Trade Details Section - New for FX trades */}
            <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#1a1a1a', borderRadius: '4px', border: '1px solid #2d2d2d' }}>
              <h4 style={{ margin: '0 0 10px 0', fontSize: '12px', color: '#00e7ff' }}>Trade Details</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '10px' }}>
                <div>
                  <strong>Counterparty:</strong> {myEntity === tradeInfo.TradeSummary["Price Maker"].Company 
                    ? tradeInfo.TradeSummary["Price Taker"].Company 
                    : tradeInfo.TradeSummary["Price Maker"].Company}
                </div>
                <div>
                  <strong>Trade Date:</strong> {tradeInfo.TradeSummary["Trade Date"]}
                </div>
                <div>
                  <strong>Maturity Date:</strong> {tradeInfo.TradeSummary.Maturity}
                </div>
                {(() => {
                  // Determine buy/sell currencies from myEntity perspective
                  const isMyEntityPriceMaker = myEntity === tradeInfo.TradeSummary["Price Maker"].Company;
                  const { Direction, "Currency 1": Currency1, "Currency 2": Currency2, "Notional Amount": notionalAmount } = tradeInfo.TradeSummary;
                  const currency2Amount = notionalAmount * tradeInfo.TradeSummary.Prices["Forward Price"];
                  
                  let buyCurrency, buyCurrencyAmount, sellCurrency, sellCurrencyAmount;
                  
                  if (isMyEntityPriceMaker) {
                    if (Direction === "Sell") {
                      sellCurrency = Currency1;
                      sellCurrencyAmount = notionalAmount;
                      buyCurrency = Currency2;
                      buyCurrencyAmount = currency2Amount;
                    } else {
                      buyCurrency = Currency1;
                      buyCurrencyAmount = notionalAmount;
                      sellCurrency = Currency2;
                      sellCurrencyAmount = currency2Amount;
                    }
                  } else {
                    // Price taker has opposite direction
                    if (Direction === "Sell") {
                      buyCurrency = Currency1;
                      buyCurrencyAmount = notionalAmount;
                      sellCurrency = Currency2;
                      sellCurrencyAmount = currency2Amount;
                    } else {
                      sellCurrency = Currency1;
                      sellCurrencyAmount = notionalAmount;
                      buyCurrency = Currency2;
                      buyCurrencyAmount = currency2Amount;
                    }
                  }
                  
                  return (
                    <>
                      <div>
                        <strong>We buy:</strong> {buyCurrency} {buyCurrencyAmount.toLocaleString()}
                      </div>
                      <div>
                        <strong>We sell:</strong> {sellCurrency} {sellCurrencyAmount.toLocaleString()}
                      </div>
                      <div>
                        <strong>Spot Price:</strong> {tradeInfo.TradeSummary.Prices["Spot Price"] !== "Not Mentioned" 
                          ? tradeInfo.TradeSummary.Prices["Spot Price"] 
                          : ""}
                      </div>
                      {tradeInfo.TradeSummary.Prices["Forward Price"] && tradeInfo.TradeSummary.Prices["Forward Price"] !== "Not Mentioned" && (
                        <div>
                          <strong>Forward Price:</strong> {tradeInfo.TradeSummary.Prices["Forward Price"]}
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
            </div>
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

      {/* Currency selection menu */}
      {showCurrencyMenu.visible && (
        <div 
          className="currency-menu"
          style={{
            position: 'absolute',
            zIndex: 1000,
            top: `${showCurrencyMenu.position.top}px`,
            left: `${showCurrencyMenu.position.left}px`,
            backgroundColor: '#1a1a1a',
            border: '1px solid #00e7ff',
            borderRadius: '4px',
            padding: '5px 0',
            boxShadow: '0 2px 10px rgba(0,0,0,0.5)',
            fontSize: '10px'
          }}
        >
          {currencyOptions.map((currency) => {
            const currencyKey = showCurrencyMenu.currencyNumber === 1 ? 'Currency 1' : 'Currency 2';
            const isSelected = tradeInfo.TradeSummary[currencyKey] === currency;
            return (
              <div
                key={currency}
                onClick={(e) => handleCurrencySelect(currency, e)}
                style={{
                  padding: '5px 15px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  backgroundColor: isSelected ? '#2a2a2a' : 'transparent',
                  transition: 'background-color 0.2s',
                  minWidth: '100px'
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#2a2a2a'}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = isSelected ? '#2a2a2a' : 'transparent'}
              >
                <span>{currency}</span>
                {isSelected && <span style={{ color: '#00e7ff' }}>✓</span>}
              </div>
            );
          })}
        </div>
      )}

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

export default FXSnipper;