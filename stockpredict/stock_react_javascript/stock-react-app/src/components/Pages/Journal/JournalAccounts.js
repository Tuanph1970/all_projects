import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { LoadingSpinner, ErrorMessage, ConfirmDialog } from '../../ui';
import { Plus, Edit3, Trash2, Shield, DollarSign, Settings, ChevronRight, BookOpen } from 'lucide-react';
import journalService from '../../../services/journalService';
import '../../../styles/journal.css';

const RULE_CATEGORIES = [
  { value: 'Risk', labelKey: 'journal.accounts.rule_risk' },
  { value: 'Entry', labelKey: 'journal.accounts.rule_entry' },
  { value: 'Exit', labelKey: 'journal.accounts.rule_exit' },
  { value: 'Psychology', labelKey: 'journal.accounts.rule_psychology' },
  { value: 'General', labelKey: 'journal.accounts.rule_general' }
];

const CURRENCIES = ['VND', 'USD', 'EUR', 'JPY', 'GBP'];

const JournalAccounts = () => {
  const { t } = useTranslation();
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  // Account form state
  const [formData, setFormData] = useState({
    account_name: '',
    starting_equity: '',
    currency: 'VND',
    max_risk_per_trade: '2.0',
    max_cumulative_risk: '25.0'
  });

  // Rules state
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [rules, setRules] = useState([]);
  const [loadingRules, setLoadingRules] = useState(false);
  const [showRuleForm, setShowRuleForm] = useState(false);
  const [ruleForm, setRuleForm] = useState({
    rule_text: '',
    category: 'General',
    sort_order: 0
  });
  const [editingRule, setEditingRule] = useState(null);

  const loadAccounts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await journalService.getAccounts();
      if (result.success) {
        setAccounts(result.data);
        // Auto-select first account if none selected
        if (result.data.length > 0 && !selectedAccountId) {
          setSelectedAccountId(result.data[0].id);
        }
      } else {
        setError(result.error?.message || t('journal.common.error_loading_accounts'));
      }
    } catch (err) {
      setError(t('journal.common.connection_error'));
    } finally {
      setLoading(false);
    }
  }, [selectedAccountId, t]);

  const loadRules = useCallback(async (accountId) => {
    if (!accountId) return;
    setLoadingRules(true);
    try {
      const result = await journalService.getRules(accountId);
      if (result.success) {
        setRules(result.data);
      }
    } catch (err) {
      console.error('Failed to load rules:', err);
    } finally {
      setLoadingRules(false);
    }
  }, []);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  useEffect(() => {
    if (selectedAccountId) {
      loadRules(selectedAccountId);
    }
  }, [selectedAccountId, loadRules]);

  const resetForm = () => {
    setFormData({
      account_name: '',
      starting_equity: '',
      currency: 'VND',
      max_risk_per_trade: '2.0',
      max_cumulative_risk: '25.0'
    });
    setEditingAccount(null);
    setShowForm(false);
  };

  const handleEditAccount = (account) => {
    setFormData({
      account_name: account.account_name,
      starting_equity: account.starting_equity.toString(),
      currency: account.currency,
      max_risk_per_trade: account.max_risk_per_trade.toString(),
      max_cumulative_risk: account.max_cumulative_risk.toString()
    });
    setEditingAccount(account);
    setShowForm(true);
  };

  const handleSubmitAccount = async (e) => {
    e.preventDefault();
    const payload = {
      account_name: formData.account_name,
      starting_equity: parseFloat(formData.starting_equity),
      currency: formData.currency,
      max_risk_per_trade: parseFloat(formData.max_risk_per_trade),
      max_cumulative_risk: parseFloat(formData.max_cumulative_risk)
    };

    let result;
    if (editingAccount) {
      result = await journalService.updateAccount(editingAccount.id, {
        account_name: payload.account_name,
        max_risk_per_trade: payload.max_risk_per_trade,
        max_cumulative_risk: payload.max_cumulative_risk,
        currency: payload.currency
      });
    } else {
      result = await journalService.createAccount(payload);
    }

    if (result.success) {
      resetForm();
      loadAccounts();
    } else {
      setError(result.error?.message || t('journal.accounts.error_saving_account'));
    }
  };

  const handleDeleteAccount = async () => {
    if (!confirmDelete) return;
    const result = await journalService.deleteAccount(confirmDelete.id);
    if (result.success) {
      setConfirmDelete(null);
      if (selectedAccountId === confirmDelete.id) {
        setSelectedAccountId(null);
        setRules([]);
      }
      loadAccounts();
    }
  };

  // =========================================================================
  // Rules handlers
  // =========================================================================

  const resetRuleForm = () => {
    setRuleForm({ rule_text: '', category: 'General', sort_order: 0 });
    setEditingRule(null);
    setShowRuleForm(false);
  };

  const handleEditRule = (rule) => {
    setRuleForm({
      rule_text: rule.rule_text,
      category: rule.category,
      sort_order: rule.sort_order
    });
    setEditingRule(rule);
    setShowRuleForm(true);
  };

  const handleSubmitRule = async (e) => {
    e.preventDefault();
    if (!selectedAccountId) return;

    const payload = {
      rule_text: ruleForm.rule_text,
      category: ruleForm.category,
      sort_order: parseInt(ruleForm.sort_order) || 0
    };

    let result;
    if (editingRule) {
      result = await journalService.updateRule(selectedAccountId, editingRule.id, payload);
    } else {
      result = await journalService.createRule(selectedAccountId, payload);
    }

    if (result.success) {
      resetRuleForm();
      loadRules(selectedAccountId);
    }
  };

  const handleToggleRule = async (rule) => {
    await journalService.updateRule(selectedAccountId, rule.id, { is_active: !rule.is_active });
    loadRules(selectedAccountId);
  };

  const handleDeleteRule = async (ruleId) => {
    await journalService.deleteRule(selectedAccountId, ruleId);
    loadRules(selectedAccountId);
  };

  const selectedAccount = accounts.find(a => a.id === selectedAccountId);

  if (loading && accounts.length === 0) {
    return <LoadingSpinner text={t('journal.accounts.loading_accounts')} />;
  }

  return (
    <div className="journal-accounts">
      <div className="journal-header">
        <div className="journal-title">
          <BookOpen size={24} />
          <h2>{t('journal.accounts.title')}</h2>
        </div>
        <button className="btn-primary" onClick={() => setShowForm(true)}>
          <Plus size={16} /> {t('journal.accounts.add_account_btn')}
        </button>
      </div>

      {error && <ErrorMessage message={error} onRetry={loadAccounts} />}

      {/* Account Form Modal */}
      {showForm && (
        <div className="journal-modal-overlay" onClick={resetForm}>
          <div className="journal-modal" onClick={e => e.stopPropagation()}>
            <h3>{editingAccount ? t('journal.accounts.edit_account_modal') : t('journal.accounts.new_account_modal')}</h3>
            <form onSubmit={handleSubmitAccount}>
              <div className="form-group">
                <label>{t('journal.accounts.account_name_label')}</label>
                <input
                  type="text"
                  value={formData.account_name}
                  onChange={e => setFormData({ ...formData, account_name: e.target.value })}
                  placeholder={t('journal.accounts.account_name_placeholder')}
                  required
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>{t('journal.accounts.starting_equity_label')}</label>
                  <input
                    type="number"
                    value={formData.starting_equity}
                    onChange={e => setFormData({ ...formData, starting_equity: e.target.value })}
                    placeholder="100000000"
                    required
                    disabled={!!editingAccount}
                  />
                </div>
                <div className="form-group">
                  <label>{t('journal.accounts.currency_label')}</label>
                  <select
                    value={formData.currency}
                    onChange={e => setFormData({ ...formData, currency: e.target.value })}
                  >
                    {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>{t('journal.accounts.max_risk_per_trade_label')}</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.max_risk_per_trade}
                    onChange={e => setFormData({ ...formData, max_risk_per_trade: e.target.value })}
                    min="0.1"
                    max="100"
                  />
                </div>
                <div className="form-group">
                  <label>{t('journal.accounts.max_cumulative_risk_label')}</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.max_cumulative_risk}
                    onChange={e => setFormData({ ...formData, max_cumulative_risk: e.target.value })}
                    min="1"
                    max="100"
                  />
                </div>
              </div>
              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={resetForm}>{t('journal.common.cancel_btn')}</button>
                <button type="submit" className="btn-primary">
                  {editingAccount ? t('journal.accounts.update_btn') : t('journal.accounts.create_btn')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Accounts List */}
      {accounts.length === 0 && !loading ? (
        <div className="journal-empty">
          <BookOpen size={48} strokeWidth={1} />
          <h3>{t('journal.common.no_accounts_title')}</h3>
          <p>{t('journal.accounts.create_first_account_hint')}</p>
          <button className="btn-primary" onClick={() => setShowForm(true)}>
            <Plus size={16} /> {t('journal.accounts.create_account_btn_empty')}
          </button>
        </div>
      ) : (
        <div className="journal-content">
          {/* Account Cards */}
          <div className="account-cards">
            {accounts.map(account => (
              <div
                key={account.id}
                className={`account-card ${selectedAccountId === account.id ? 'selected' : ''}`}
                onClick={() => setSelectedAccountId(account.id)}
              >
                <div className="account-card-header">
                  <h4>{account.account_name}</h4>
                  <div className="account-card-actions">
                    <button className="btn-icon" onClick={(e) => { e.stopPropagation(); handleEditAccount(account); }}>
                      <Edit3 size={14} />
                    </button>
                    <button className="btn-icon btn-danger" onClick={(e) => { e.stopPropagation(); setConfirmDelete(account); }}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
                <div className="account-card-body">
                  <div className="account-stat">
                    <DollarSign size={14} />
                    <span className="stat-label">{t('journal.accounts.current_equity_label')}</span>
                    <span className="stat-value">{journalService.formatCurrency(account.current_equity, account.currency)}</span>
                  </div>
                  <div className="account-stat">
                    <Shield size={14} />
                    <span className="stat-label">{t('journal.accounts.risk_per_trade_label')}</span>
                    <span className="stat-value">{account.max_risk_per_trade}%</span>
                  </div>
                  <div className="account-stat">
                    <Settings size={14} />
                    <span className="stat-label">{t('journal.accounts.cumulative_risk_label')}</span>
                    <span className="stat-value">{account.max_cumulative_risk}%</span>
                  </div>
                </div>
                {selectedAccountId === account.id && <ChevronRight size={16} className="account-selected-icon" />}
              </div>
            ))}
          </div>

          {/* Trading Rules Section */}
          {selectedAccount && (
            <div className="rules-section">
              <div className="rules-header">
                <h3>{t('journal.accounts.trading_rules_header', { accountName: selectedAccount.account_name })}</h3>
                <button className="btn-primary btn-sm" onClick={() => setShowRuleForm(true)}>
                  <Plus size={14} /> {t('journal.accounts.add_rule_btn')}
                </button>
              </div>

              {/* Rule Form */}
              {showRuleForm && (
                <div className="rule-form">
                  <form onSubmit={handleSubmitRule}>
                    <div className="form-row">
                      <div className="form-group flex-2">
                        <input
                          type="text"
                          value={ruleForm.rule_text}
                          onChange={e => setRuleForm({ ...ruleForm, rule_text: e.target.value })}
                          placeholder={t('journal.accounts.rule_placeholder')}
                          required
                        />
                      </div>
                      <div className="form-group">
                        <select
                          value={ruleForm.category}
                          onChange={e => setRuleForm({ ...ruleForm, category: e.target.value })}
                        >
                          {RULE_CATEGORIES.map(c => (
                            <option key={c.value} value={c.value}>{t(c.labelKey)}</option>
                          ))}
                        </select>
                      </div>
                      <div className="form-actions-inline">
                        <button type="submit" className="btn-primary btn-sm">
                          {editingRule ? t('journal.accounts.rule_update_btn') : t('journal.accounts.rule_add_btn')}
                        </button>
                        <button type="button" className="btn-secondary btn-sm" onClick={resetRuleForm}>{t('journal.accounts.rule_cancel_btn')}</button>
                      </div>
                    </div>
                  </form>
                </div>
              )}

              {/* Rules List */}
              {loadingRules ? (
                <LoadingSpinner text={t('journal.accounts.loading_rules')} />
              ) : rules.length === 0 ? (
                <div className="rules-empty">
                  <p>{t('journal.accounts.no_rules_hint')}</p>
                </div>
              ) : (
                <div className="rules-list">
                  {RULE_CATEGORIES.map(cat => {
                    const categoryRules = rules.filter(r => r.category === cat.value);
                    if (categoryRules.length === 0) return null;
                    return (
                      <div key={cat.value} className="rule-category-group">
                        <h4 className="rule-category-title">{t(cat.labelKey)}</h4>
                        {categoryRules.map(rule => (
                          <div key={rule.id} className={`rule-item ${!rule.is_active ? 'rule-inactive' : ''}`}>
                            <label className="rule-checkbox">
                              <input
                                type="checkbox"
                                checked={rule.is_active}
                                onChange={() => handleToggleRule(rule)}
                              />
                              <span className="rule-text">{rule.rule_text}</span>
                            </label>
                            <div className="rule-actions">
                              <button className="btn-icon" onClick={() => handleEditRule(rule)}>
                                <Edit3 size={12} />
                              </button>
                              <button className="btn-icon btn-danger" onClick={() => handleDeleteRule(rule.id)}>
                                <Trash2 size={12} />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Delete Confirmation */}
      {confirmDelete && (
        <ConfirmDialog
          title={t('journal.accounts.delete_account_confirm_title')}
          message={t('journal.accounts.delete_account_confirm_msg', { accountName: confirmDelete.account_name })}
          onConfirm={handleDeleteAccount}
          onCancel={() => setConfirmDelete(null)}
          confirmText={t('journal.accounts.delete_btn')}
          cancelText={t('journal.accounts.cancel_delete_btn')}
          variant="danger"
        />
      )}
    </div>
  );
};

export default JournalAccounts;
