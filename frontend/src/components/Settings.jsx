import React, { useState, useEffect } from 'react';
import { Trash2, Plus, Upload, Search } from 'lucide-react';
import Papa from 'papaparse';

const Settings = ({ onClose }) => {
  const [myEntity, setMyEntity] = useState('');
  const [aiProvider, setAIProvider] = useState('');
  const [myName, setMyName] = useState('');
  const [personCompanyPairs, setPersonCompanyPairs] = useState([
    { person: '', company: '' }
  ]);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [pendingCsvData, setPendingCsvData] = useState(null);
  const [uploadKey, setUploadKey] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const [validationError, setValidationError] = useState('');

  useEffect(() => {
    const storedEntity = localStorage.getItem('myEntity');
    const storedAIProvider = localStorage.getItem('aiProvider');
    const storedName = localStorage.getItem('myName');
    const storedPairs = localStorage.getItem('personCompanyPairs');
    
    if (storedEntity) setMyEntity(storedEntity);
    if (storedAIProvider) setAIProvider(storedAIProvider);
    if (storedName) setMyName(storedName);
    if (storedPairs) setPersonCompanyPairs(JSON.parse(storedPairs));
  }, []);

  const handlePairChange = (index, field, value) => {
    const currentPairs = searchTerm ? filteredPairs : personCompanyPairs;
    const targetPair = currentPairs[index];
    
    // Find the actual index in the full array
    const originalIndex = personCompanyPairs.findIndex(
      pair => pair.person === targetPair.person && pair.company === targetPair.company
    );
    
    const newPairs = [...personCompanyPairs];
    newPairs[originalIndex][field] = value;
    setPersonCompanyPairs(newPairs);
  };

  const addPair = () => {
    setPersonCompanyPairs([...personCompanyPairs, { person: '', company: '' }]);
  };

  const removePair = (index) => {
    const newPairs = personCompanyPairs.filter((_, i) => i !== index);
    setPersonCompanyPairs(newPairs);
  };

  const validatePairs = () => {
    const emptyFields = personCompanyPairs.filter(pair => 
      !pair.person.trim() || !pair.company.trim()
    );
    
    if (emptyFields.length > 0) {
      setValidationError('Please fill in all Person and Company fields before saving.');
      return false;
    }
    
    setValidationError('');
    return true;
  };

  const processCsvData = (results, mode) => {
    const validPairs = results.data
      .filter(row => row.length >= 2)
      .map(row => ({
        person: row[0]?.trim() || '',
        company: row[1]?.trim() || ''
      }))
      .filter(pair => pair.person || pair.company);
    
    if (validPairs.length > 0) {
      if (mode === 'overwrite') {
        setPersonCompanyPairs(validPairs);
      } else if (mode === 'append') {
        setPersonCompanyPairs(prev => [...prev, ...validPairs]);
      }
    }
    setPendingCsvData(null);
    setUploadKey(prev => prev + 1); // Add this line to reset the input
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      Papa.parse(file, {
        complete: (results) => {
          setPendingCsvData(results);
          setShowUploadDialog(true);
        },
        header: false,
        skipEmptyLines: true
      });
    }
  };

  const savePreferences = () => {
    if (!validatePairs()) {
      return;
    }
    
    localStorage.setItem('myEntity', myEntity);
    localStorage.setItem('aiProvider', aiProvider);
    localStorage.setItem('myName', myName);
    localStorage.setItem('personCompanyPairs', JSON.stringify(personCompanyPairs));
    alert('Settings saved!');
    onClose();
  };

  const inputStyle = {
    width: 'calc(100% - 20px)',
    padding: '6px',
    border: '1px solid #00e7ff',
    borderRadius: '4px',
    backgroundColor: 'black',
    color: 'white',
    fontFamily: 'Manrope, sans-serif',
    fontSize: '12px',
  };

  const pairInputStyle = {
    ...inputStyle,
    padding: '3px',
    fontSize: '10px',
    width: '45%',
  };

  const labelStyle = {
    display: 'block',
    marginBottom: '4px',
    fontSize: '12px',
  };

  const pairLabelStyle = {
    ...labelStyle,
    fontSize: '10px',
    marginBottom: '2px',
  };

  const searchInputStyle = {
    ...inputStyle,
    marginBottom: '8px',
    fontSize: '10px',
    padding: '3px 6px',
  };

  const UploadDialog = ({ onCancel, onAppend, onOverwrite }) => {
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000
      }}>
        <div style={{
          backgroundColor: '#1c1c1c',
          borderRadius: '8px',
          padding: '15px',
          border: '1px solid #00e7ff',
          width: '300px',
          maxWidth: '90%',
        }}>
          <h3 style={{ 
            color: 'white', 
            fontSize: '12px', 
            marginTop: 0,
            marginBottom: '10px'
          }}>
            Upload CSV Data
          </h3>
          <p style={{ 
            color: 'white', 
            fontSize: '10px',
            marginBottom: '15px'
          }}>
            How would you like to add the new data?
          </p>
          <div style={{
            display: 'flex',
            gap: '10px',
            justifyContent: 'flex-end'
          }}>
            <button
              onClick={onCancel}
              style={{
                padding: '4px 8px',
                backgroundColor: 'transparent',
                color: '#00e7ff',
                border: '1px solid #00e7ff',
                borderRadius: '4px',
                fontSize: '10px',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              onClick={onAppend}
              style={{
                padding: '4px 8px',
                backgroundColor: '#00e7ff',
                color: 'black',
                border: 'none',
                borderRadius: '4px',
                fontSize: '10px',
                cursor: 'pointer'
              }}
            >
              Append
            </button>
            <button
              onClick={onOverwrite}
              style={{
                padding: '4px 8px',
                backgroundColor: '#00e7ff',
                color: 'black',
                border: 'none',
                borderRadius: '4px',
                fontSize: '10px',
                cursor: 'pointer'
              }}
            >
              Overwrite
            </button>
          </div>
        </div>
      </div>
    );
  };

  // New function to handle search visibility
  const toggleSearch = () => {
    setShowSearch(!showSearch);
    if (!showSearch) {
      setSearchTerm('');
    }
  };

  // New filter function added
  const filteredPairs = personCompanyPairs.filter(pair => {
    const search = searchTerm.toLowerCase();
    return pair.person.toLowerCase().includes(search) || 
          pair.company.toLowerCase().includes(search);
  });

  return (
    <>
      <div
        style={{
          backgroundColor: '#1c1c1c',
          color: 'white',
          fontFamily: 'Manrope, sans-serif',
          borderRadius: '8px',
          padding: '15px',
          position: 'relative',
          boxShadow: '0 0 15px rgba(0, 231, 255, 0.7)',
          width: '300px',
          maxWidth: '90%',
          margin: '0 auto',
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '4px',
            right: '4px',
            background: 'none',
            border: 'none',
            color: '#00e7ff',
            fontSize: '14px',
            cursor: 'pointer',
            padding: '2px',
          }}
          aria-label="Close"
        >
          ✖
        </button>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '15px',
            flexShrink: 0  // Prevents header from shrinking
          }}
        >
          <img
            src="palace_blanco.png"
            alt="Palace Logo"
            style={{ height: '20px' }}
          />
          <h1 style={{ fontSize: '12px', margin: 0 }}>Settings</h1>
        </div>

        <div style={{
          overflowY: 'auto',
          flexGrow: 1,
          marginRight: '-8px',
          paddingRight: '8px'
        }}>
          <div style={{ marginBottom: '12px' }}>
            <label style={labelStyle}>
              My Name:
            </label>
            <input
              type="text"
              value={myName}
              onChange={(e) => setMyName(e.target.value)}
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: '12px' }}>
            <label style={labelStyle}>
              My Entity:
            </label>
            <input
              type="text"
              value={myEntity}
              onChange={(e) => setMyEntity(e.target.value)}
              style={inputStyle}
            />
          </div>

          <div style={{ marginBottom: '12px' }}>
            <label style={labelStyle}>
              AI Provider:
            </label>
            <select
              value={aiProvider}
              onChange={(e) => setAIProvider(e.target.value)}
              style={{
                ...inputStyle,
                width: '100%',
              }}
            >
              <option value="Anthropic">Anthropic</option>
              <option value="Google">Google</option>
              <option value="OpenAI">Open AI</option>
            </select>
          </div>

          <div style={{ marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2px' }}>
              <label style={pairLabelStyle}>Person-Company Pairs:</label>
              <div style={{ marginLeft: 'auto', display: 'flex', gap: '2px' }}>
                <button
                  onClick={toggleSearch}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: showSearch ? '#00e7ff' : '#ffffff',
                    cursor: 'pointer',
                    padding: '1px',
                  }}
                  title="Search pairs"
                >
                  <Search size={14} />
                </button>
                <button
                  onClick={addPair}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#00e7ff',
                    cursor: 'pointer',
                    padding: '1px',
                  }}
                  title="Add new pair"
                >
                  <Plus size={14} />
                </button>
                <label style={{
                  color: '#00e7ff',
                  cursor: 'pointer',
                  padding: '1px',
                }}>
                  <Upload size={14} />
                    <input
                      key={uploadKey}
                      type="file"
                      accept=".csv"
                      onChange={handleFileUpload}
                      style={{ display: 'none' }}
                    />
                </label>
              </div>
            </div>
          </div>

          {/* New conditional search input field */}
          {showSearch && (
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search persons or companies..."
              style={searchInputStyle}
            />
          )}

          {(searchTerm ? filteredPairs : personCompanyPairs).map((pair, index) => (
            <div key={index} style={{ display: 'flex', gap: '2px', marginBottom: '3px' }}>
              <input
                type="text"
                value={pair.person}
                onChange={(e) => handlePairChange(index, 'person', e.target.value)}
                placeholder="Person Name"
                style={pairInputStyle}
              />
              <input
                type="text"
                value={pair.company}
                onChange={(e) => handlePairChange(index, 'company', e.target.value)}
                placeholder="Company Name"
                style={pairInputStyle}
              />
              {personCompanyPairs.length > 1 && (
                <button
                  onClick={() => removePair(index)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#ff4444',
                    cursor: 'pointer',
                    padding: '1px',
                  }}
                  title="Remove pair"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
        </div>

        {validationError && (
          <div style={{
            color: '#ff4444',
            fontSize: '10px',
            marginBottom: '8px',
            textAlign: 'center',
            flexShrink: 0
          }}>
            {validationError}
          </div>
        )}

        <button
          onClick={savePreferences}
          style={{
            padding: '6px 12px',
            backgroundColor: '#00e7ff',
            color: 'black',
            border: 'none',
            borderRadius: '4px',
            fontSize: '12px',
            fontWeight: 'bold',
            cursor: 'pointer',
            width: '100%',
            flexShrink: 0
          }}
        >
          Save Settings
        </button>
      </div>

      {showUploadDialog && (
        <UploadDialog
          onCancel={() => {
            setPendingCsvData(null);
            setShowUploadDialog(false);
          }}
          onAppend={() => {
            processCsvData(pendingCsvData, 'append');
            setShowUploadDialog(false);
          }}
          onOverwrite={() => {
            processCsvData(pendingCsvData, 'overwrite');
            setShowUploadDialog(false);
          }}
        />
      )}
    </>
  );
};

export default Settings;