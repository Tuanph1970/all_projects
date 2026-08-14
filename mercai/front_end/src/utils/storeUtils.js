// Store utilities to avoid circular dependencies
let storeInstance = null;

export const setStoreInstance = (store) => {
  storeInstance = store;
};

export const getStoreInstance = () => {
  return storeInstance;
};

export const dispatchToStore = (action) => {
  if (storeInstance) {
    return storeInstance.dispatch(action);
  }
  console.warn('Store instance not available');
  return Promise.resolve();
};