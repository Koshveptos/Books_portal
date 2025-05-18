import React from 'react';
import { FavoriteButtonProps } from '../types';

export const FavoriteButton: React.FC<FavoriteButtonProps> = ({ isFavorite, onClick, disabled = false, className = '' }) => {
    return (
        <button
            onClick={onClick}
            disabled={disabled}
            className={`text-2xl transition-colors ${
                disabled
                    ? 'text-gray-300 cursor-not-allowed'
                    : 'text-gray-400 hover:text-yellow-500 cursor-pointer'
            } ${isFavorite ? 'text-yellow-500' : ''} ${className}`}
            title={isFavorite ? 'Удалить из избранного' : 'Добавить в избранное'}
        >
            ♥
        </button>
    );
};

export default FavoriteButton;
