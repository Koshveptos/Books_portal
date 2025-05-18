import React from 'react';
import { LikeButtonProps } from '../types';

export const LikeButton: React.FC<LikeButtonProps> = ({ isLiked, onClick, disabled = false, className = '' }) => {
    return (
        <button
            onClick={onClick}
            disabled={disabled}
            className={`text-2xl transition-colors ${
                disabled
                    ? 'text-gray-300 cursor-not-allowed'
                    : 'text-gray-400 hover:text-red-500 cursor-pointer'
            } ${isLiked ? 'text-red-500' : ''} ${className}`}
            title={isLiked ? 'Убрать лайк' : 'Поставить лайк'}
        >
            👍
        </button>
    );
};

export default LikeButton;
